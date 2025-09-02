// Global variables
let adminWebSocket = null;
let currentRejectVoterId = null;
let currentRejectVoterName = null;
let electionCharts = {};
let realTimeCharts = {};

// Initialize the admin dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    populateYearDropdown();
    setupFormHandlers();
    loadAuditLogs();
    startHeartbeat();
    initializeCharts();
    loadElectionStatistics();
    startRealTimeUpdates();
});

// WebSocket connection for real-time updates
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/admin/`;
    
    adminWebSocket = new WebSocket(wsUrl);
    
    adminWebSocket.onopen = function() {
        console.log('WebSocket connection established');
        addActivityLog('Connected to real-time monitoring system');
    };
    
    adminWebSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    adminWebSocket.onclose = function() {
        console.log('WebSocket connection closed');
        addActivityLog('Disconnected from real-time monitoring', 'warning');
        // Attempt to reconnect after 5 seconds
        setTimeout(initializeWebSocket, 5000);
    };
    
    adminWebSocket.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'voter_registered':
            handleNewVoter(data.voter);
            break;
        case 'vote_cast':
            handleVoteCast(data.vote);
            updateElectionResults(data.vote.election_id);
            break;
        case 'system_health':
            updateSystemHealth(data.health);
            break;
        case 'consensus_update':
            updateConsensus(data.consensus);
            break;
        case 'node_status':
            updateNodeStatus(data.node);
            break;
        case 'election_started':
            handleElectionStarted(data.election);
            break;
        case 'election_ended':
            handleElectionEnded(data.election);
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
}

// Handle new voter registration
function handleNewVoter(voter) {
    // Update pending voters count
    const pendingCount = document.getElementById('pendingCount');
    const pendingBadge = document.getElementById('pendingBadge');
    const newCount = parseInt(pendingCount.textContent) + 1;
    
    pendingCount.textContent = newCount;
    pendingBadge.textContent = newCount;
    
    // Add to pending voters table if we're on that tab
    const pendingTable = document.querySelector('#pendingVotersTable tbody');
    if (pendingTable && document.querySelector('#pending-voters-tab').classList.contains('active')) {
        const newRow = createPendingVoterRow(voter);
        pendingTable.insertBefore(newRow, pendingTable.firstChild);
    }
    
    // Add to activity log
    addActivityLog(`New voter registration: ${voter.full_name} (${voter.voter_id})`);
}

// Handle vote cast event
function handleVoteCast(vote) {
    addActivityLog(`Vote cast in ${vote.election_name}: ${vote.voter_id} voted for ${vote.candidate_name}`);
    
    // Update real-time charts if visible
    if (document.querySelector('#monitoring-tab').classList.contains('active')) {
        updateVoteQueueChart();
        updateConsensusMonitor();
    }
}

// Handle election started event
function handleElectionStarted(election) {
    addActivityLog(`Election started: ${election.name}`, 'success');
    updateElectionStatus(election.id, 'active');
}

// Handle election ended event
function handleElectionEnded(election) {
    addActivityLog(`Election ended: ${election.name}`, 'warning');
    updateElectionStatus(election.id, 'completed');
    finalizeElectionResults(election.id);
}


// Create a new row for the pending voters table
function createPendingVoterRow(voter) {
    const row = document.createElement('tr');
    row.id = `voter-${voter.id}`;
    
    row.innerHTML = `
        <td>${voter.voter_id}</td>
        <td>${voter.full_name}</td>
        <td>${voter.email}</td>
        <td>${voter.city}, ${voter.state}</td>
        <td>${new Date(voter.created_at).toLocaleDateString()}</td>
        <td>
            <div class="voter-actions">
                <button class="btn btn-sm btn-approve" onclick="approveVoter('${voter.id}', '${voter.voter_id}')">
                    <i class="fas fa-check"></i> Approve
                </button>
                <button class="btn btn-sm btn-reject" onclick="showRejectModal('${voter.id}', '${voter.voter_id}')">
                    <i class="fas fa-times"></i> Reject
                </button>
                <button class="btn btn-sm btn-outline-info" onclick="viewVoterDetails('${voter.id}')">
                    <i class="fas fa-eye"></i> View
                </button>
            </div>
        </td>
    `;
    
    return row;
}

// Approve a voter
function approveVoter(voterId, voterIdText) {
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    
    // Show loading state
    button.disabled = true;
    button.innerHTML = '<span class="loading-spinner" style="display:inline-block;"></span> Processing...';
    
    // Send approval request
    fetch(`/api/approve-voter/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({ voter_id: voterId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove from pending table
            const row = document.getElementById(`voter-${voterId}`);
            if (row) row.remove();
            
            // Update counters
            updateVoterCounters(-1, 1, 0);
            
            // Show success message
            showToast('Voter approved successfully', 'success');
            addActivityLog(`Approved voter: ${voterIdText}`);
        } else {
            throw new Error(data.message || 'Failed to approve voter');
        }
    })
    .catch(error => {
        showToast(error.message, 'error');
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

// Show reject voter modal
function showRejectModal(voterId, voterIdText) {
    currentRejectVoterId = voterId;
    currentRejectVoterName = voterIdText;
    
    document.getElementById('rejectVoterName').textContent = voterIdText;
    document.getElementById('rejectionReason').value = '';
    
    const modal = new bootstrap.Modal(document.getElementById('rejectVoterModal'));
    modal.show();
}

// Confirm voter rejection
function confirmRejectVoter() {
    const reason = document.getElementById('rejectionReason').value;
    const button = document.querySelector('#rejectVoterModal .btn-danger');
    const originalText = button.innerHTML;
    
    if (!reason.trim()) {
        showToast('Please provide a reason for rejection', 'warning');
        return;
    }
    
    // Show loading state
    button.disabled = true;
    button.innerHTML = '<span class="loading-spinner" style="display:inline-block;"></span> Processing...';
    
    // Send rejection request
    fetch(`/api/reject-voter/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            voter_id: currentRejectVoterId,
            reason: reason
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove from pending table
            const row = document.getElementById(`voter-${currentRejectVoterId}`);
            if (row) row.remove();
            
            // Update counters
            updateVoterCounters(-1, 0, 1);
            
            // Close modal and show success message
            bootstrap.Modal.getInstance(document.getElementById('rejectVoterModal')).hide();
            showToast('Voter rejected successfully', 'success');
            addActivityLog(`Rejected voter: ${currentRejectVoterName} - Reason: ${reason}`);
        } else {
            throw new Error(data.message || 'Failed to reject voter');
        }
    })
    .catch(error => {
        showToast(error.message, 'error');
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

// Update voter counters
function updateVoterCounters(pendingDelta, approvedDelta, rejectedDelta) {
    const pendingCount = document.getElementById('pendingCount');
    const pendingBadge = document.getElementById('pendingBadge');
    const approvedCount = document.getElementById('approvedCount');
    const approvedBadge = document.getElementById('approvedBadge');
    const rejectedBadge = document.getElementById('rejectedBadge');
    
    if (pendingCount && pendingDelta) {
        const newPending = Math.max(0, parseInt(pendingCount.textContent) + pendingDelta);
        pendingCount.textContent = newPending;
        pendingBadge.textContent = newPending;
    }
    
    if (approvedCount && approvedDelta) {
        const newApproved = Math.max(0, parseInt(approvedCount.textContent) + approvedDelta);
        approvedCount.textContent = newApproved;
        approvedBadge.textContent = newApproved;
    }
    
    if (rejectedBadge && rejectedDelta) {
        const newRejected = Math.max(0, parseInt(rejectedBadge.textContent) + rejectedDelta);
        rejectedBadge.textContent = newRejected;
    }
}

// Populate year dropdown for election creation
function populateYearDropdown() {
    const yearSelect = document.getElementById('electionYear');
    if (!yearSelect) return;
    
    const currentYear = new Date().getFullYear();
    for (let i = currentYear; i <= currentYear + 5; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = i;
        yearSelect.appendChild(option);
    }
}

// Setup form handlers
function setupFormHandlers() {
    // Election creation form
    const electionForm = document.getElementById('createElectionForm');
    if (electionForm) {
        electionForm.addEventListener('submit', handleCreateElection);
    }
    
    // Candidate addition form
    const candidateForm = document.getElementById('addCandidateForm');
    if (candidateForm) {
        candidateForm.addEventListener('submit', handleAddCandidate);
    }
}

// Handle election creation form submission
function handleCreateElection(event) {
    event.preventDefault();
    
    const submitButton = document.getElementById('createElectionSubmit');
    const originalText = submitButton.innerHTML;
    
    // Show loading state
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading-spinner" style="display:inline-block;"></span> Creating...';
    
    // Prepare form data
    const formData = {
        name: document.getElementById('electionName').value,
        election_type: document.getElementById('electionType').value,
        state: document.getElementById('electionState').value,
        start_date: document.getElementById('startDateTime').value,
        end_date: document.getElementById('endDateTime').value,
        replication_factor: document.getElementById('replicationFactor').value,
        consensus_threshold: document.getElementById('consensusThreshold').value,
    };
    
    // Send request
    fetch('/api/create-election/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify(formData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal and show success message
            bootstrap.Modal.getInstance(document.getElementById('createElectionModal')).hide();
            showToast('Election created successfully', 'success');
            addActivityLog(`Created election: ${formData.name}`);
            
            // Reload the page to show the new election
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(data.message || 'Failed to create election');
        }
    })
    .catch(error => {
        showToast(error.message, 'error');
        submitButton.disabled = false;
        submitButton.innerHTML = originalText;
    });
}

// Handle candidate addition form submission
function handleAddCandidate(event) {
    event.preventDefault();
    
    const submitButton = document.getElementById('addCandidateSubmit');
    const originalText = submitButton.innerHTML;
    
    // Show loading state
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading-spinner" style="display:inline-block;"></span> Adding...';
    
    // Prepare form data
    const formData = {
        election: document.getElementById('candidateElection').value,
        name: document.getElementById('candidateName').value,
        party: document.getElementById('candidateParty').value,
        constituency: document.getElementById('candidateConstituency').value,
        symbol: document.getElementById('candidateSymbol').value,
        education: document.getElementById('candidateEducation').value,
    };
    
    // Send request
    fetch('/api/add-candidate/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify(formData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal and show success message
            bootstrap.Modal.getInstance(document.getElementById('addCandidateModal')).hide();
            showToast('Candidate added successfully', 'success');
            addActivityLog(`Added candidate: ${formData.name}`);
            
            // Reload the page to show the new candidate
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(data.message || 'Failed to add candidate');
        }
    })
    .catch(error => {
        showToast(error.message, 'error');
        submitButton.disabled = false;
        submitButton.innerHTML = originalText;
    });
}

// Load audit logs
function loadAuditLogs() {
    const auditTable = document.getElementById('auditLogsTable');
    if (!auditTable) return;
    
    fetch('/api/audit-logs/')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            renderAuditLogs(data.logs);
        } else {
            throw new Error('Failed to load audit logs');
        }
    })
    .catch(error => {
        console.error('Error loading audit logs:', error);
        auditTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Error loading audit logs</td></tr>';
    });
}

// Render audit logs to the table
function renderAuditLogs(logs) {
    const tbody = document.querySelector('#auditLogsTable tbody');
    if (!tbody) return;
    
    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No audit logs found</td></tr>';
        return;
    }
    
    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${new Date(log.timestamp).toLocaleString()}</td>
            <td><span class="badge bg-secondary">${log.log_type}</span></td>
            <td>${log.user || 'System'}</td>
            <td>${log.details}</td>
            <td>${log.ip_address || 'N/A'}</td>
            <td><small class="text-muted">${log.hash_chain.substring(0, 12)}...</small></td>
        </tr>
    `).join('');
}

// Filter audit logs
function filterAuditLogs() {
    const typeFilter = document.getElementById('logTypeFilter').value;
    const dateFilter = document.getElementById('dateFilter').value;
    
    let url = '/api/audit-logs/';
    const params = [];
    
    if (typeFilter) params.push(`type=${typeFilter}`);
    if (dateFilter) params.push(`date=${dateFilter}`);
    
    if (params.length > 0) {
        url += '?' + params.join('&');
    }
    
    fetch(url)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            renderAuditLogs(data.logs);
        } else {
            throw new Error('Failed to filter audit logs');
        }
    })
    .catch(error => {
        console.error('Error filtering audit logs:', error);
        showToast('Error filtering audit logs', 'error');
    });
}

// Export audit logs
function exportAuditLogs() {
    const typeFilter = document.getElementById('logTypeFilter').value;
    const dateFilter = document.getElementById('dateFilter').value;
    
    let url = '/api/export-audit-logs/';
    const params = [];
    
    if (typeFilter) params.push(`type=${typeFilter}`);
    if (dateFilter) params.push(`date=${dateFilter}`);
    
    if (params.length > 0) {
        url += '?' + params.join('&');
    }
    
    // Trigger download
    window.location.href = url;
}


// Initialize charts
function initializeCharts() {
    initializeElectionChart();
    initializeVoteQueueChart();
    initializeNodePerformanceChart();
}

// Initialize election statistics chart
function initializeElectionChart() {
    const ctx = document.getElementById('electionChart');
    if (!ctx) return;
    
    electionCharts.statistics = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Active', 'Upcoming', 'Completed'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ['#28a745', '#ffc107', '#6c757d']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Initialize vote queue chart
function initializeVoteQueueChart() {
    const ctx = document.getElementById('voteQueueChart');
    if (!ctx) return;
    
    realTimeCharts.voteQueue = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Votes in Queue',
                data: [],
                borderColor: '#138808',
                backgroundColor: 'rgba(19, 136, 8, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Initialize node performance chart
function initializeNodePerformanceChart() {
    const ctx = document.getElementById('nodePerformanceChart');
    if (!ctx) return;
    
    realTimeCharts.nodePerformance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Response Time (ms)',
                data: [],
                backgroundColor: '#f58220'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}


// Load election statistics
function loadElectionStatistics() {
    fetch('/api/election-statistics/')
    .then(response => response.json())
    .then(data => {
        if (data.success && electionCharts.statistics) {
            electionCharts.statistics.data.datasets[0].data = [
                data.stats.active,
                data.stats.upcoming,
                data.stats.completed
            ];
            electionCharts.statistics.update();
        }
    })
    .catch(error => console.error('Error loading election statistics:', error));
}


// Start real-time updates
function startRealTimeUpdates() {
    // Update charts every 10 seconds
    setInterval(() => {
        updateVoteQueueChart();
        updateNodePerformanceChart();
        updateConsensusMonitor();
    }, 10000);
}

// Update vote queue chart
function updateVoteQueueChart() {
    if (!realTimeCharts.voteQueue) return;
    
    fetch('/api/vote-queue-status/')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const chart = realTimeCharts.voteQueue;
            const now = new Date().toLocaleTimeString();
            
            chart.data.labels.push(now);
            chart.data.datasets[0].data.push(data.queue_size);
            
            // Keep only last 20 data points
            if (chart.data.labels.length > 20) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
            
            chart.update();
        }
    })
    .catch(error => console.error('Error updating vote queue chart:', error));
}

// Update node performance chart
function updateNodePerformanceChart() {
    if (!realTimeCharts.nodePerformance) return;
    
    fetch('/api/node-performance/')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const chart = realTimeCharts.nodePerformance;
            chart.data.labels = data.nodes.map(node => node.node_id);
            chart.data.datasets[0].data = data.nodes.map(node => node.response_time);
            chart.update();
        }
    })
    .catch(error => console.error('Error updating node performance chart:', error));
}

// Update consensus monitor
function updateConsensusMonitor() {
    const monitor = document.getElementById('consensusMonitor');
    if (!monitor) return;
    
    fetch('/api/consensus-status/')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            monitor.innerHTML = data.processes.map(process => `
                <div class="border rounded p-2 mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${process.election_name}</strong>
                            <small class="text-muted">Round ${process.consensus_round}</small>
                        </div>
                        <div class="consensus-progress" style="width: 200px;">
                            <div class="consensus-bar" style="width: ${process.progress}%"></div>
                        </div>
                        <span class="badge bg-${process.status === 'achieved' ? 'success' : 'warning'}">
                            ${process.status}
                        </span>
                    </div>
                </div>
            `).join('');
        }
    })
    .catch(error => console.error('Error updating consensus monitor:', error));
}


// Add activity log entry
function addActivityLog(message, type = 'info') {
    const activityLog = document.getElementById('activityLog');
    if (!activityLog) return;
    
    const icon = type === 'warning' ? 'exclamation-triangle' : 
                 type === 'error' ? 'exclamation-circle' : 
                 type === 'success' ? 'check-circle' : 'info-circle';
    
    const item = document.createElement('div');
    item.className = `activity-item ${type !== 'info' ? 'text-' + type : ''}`;
    item.innerHTML = `<i class="fas fa-${icon}"></i> ${new Date().toLocaleTimeString()}: ${message}`;
    
    activityLog.insertBefore(item, activityLog.firstChild);
    
    // Limit to 100 entries
    if (activityLog.children.length > 100) {
        activityLog.removeChild(activityLog.lastChild);
    }
    
    // Auto-scroll to top
    activityLog.scrollTop = 0;
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return;
    
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.id = toastId;
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 5000
    });
    
    bsToast.show();
    
    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Get CSRF token for Django
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    
    return cookieValue;
}

// Start heartbeat for real-time counters
function startHeartbeat() {
    setInterval(updateRealTimeCounters, 30000); // Update every 30 seconds
    updateRealTimeCounters(); // Initial update
}

// Update real-time counters
function updateRealTimeCounters() {
    fetch('/api/admin-stats/')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update counters
            document.getElementById('pendingCount').textContent = data.stats.pending_count;
            document.getElementById('approvedCount').textContent = data.stats.approved_count;
            document.getElementById('activeElections').textContent = data.stats.active_elections;
            document.getElementById('systemHealth').textContent = data.stats.system_health.toFixed(1) + '%';
            document.getElementById('activeNodes').textContent = data.stats.active_nodes;
            
            // Update badges
            document.getElementById('pendingBadge').textContent = data.stats.pending_count;
            document.getElementById('approvedBadge').textContent = data.stats.approved_count;
            document.getElementById('rejectedBadge').textContent = data.stats.rejected_count;
        }
    })
    .catch(error => {
        console.error('Error updating real-time counters:', error);
    });
}

// Real election tracking functions (replacing placeholders)
function viewVoterDetails(voterId) {
    fetch(`/api/voter-details/${voterId}/`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showVoterDetailsModal(data.voter);
        } else {
            showToast('Failed to load voter details', 'error');
        }
    })
    .catch(error => {
        console.error('Error loading voter details:', error);
        showToast('Error loading voter details', 'error');
    });
}

function reconsiderVoter(voterId) {
    if (confirm('Are you sure you want to reconsider this rejected voter?')) {
        fetch('/api/reconsider-voter/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ voter_id: voterId }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Voter moved back to pending approval', 'success');
                addActivityLog(`Reconsidered voter: ${data.voter_id}`);
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showToast(data.message || 'Failed to reconsider voter', 'error');
            }
        })
        .catch(error => {
            showToast('Error reconsidering voter', 'error');
        });
    }
}

function monitorElection(electionId) {
    // Open election monitoring modal or navigate to detailed view
    showElectionMonitoringModal(electionId);
}

function manageElection(electionId) {
    // Open election management modal
    showElectionManagementModal(electionId);
}

function startElection(electionId) {
    if (confirm('Are you sure you want to start this election? This action cannot be undone.')) {
        fetch('/api/start-election/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ election_id: electionId }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Election started successfully', 'success');
                addActivityLog(`Started election: ${data.election_name}`);
                updateElectionStatus(electionId, 'active');
            } else {
                showToast(data.message || 'Failed to start election', 'error');
            }
        })
        .catch(error => {
            showToast('Error starting election', 'error');
        });
    }
}

function endElection(electionId) {
    if (confirm('Are you sure you want to end this election? This will finalize all results.')) {
        fetch('/api/end-election/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ election_id: electionId }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Election ended successfully', 'success');
                addActivityLog(`Ended election: ${data.election_name}`);
                updateElectionStatus(electionId, 'completed');
                finalizeElectionResults(electionId);
            } else {
                showToast(data.message || 'Failed to end election', 'error');
            }
        })
        .catch(error => {
            showToast('Error ending election', 'error');
        });
    }
}

function viewCandidate(candidateId) {
    fetch(`/api/candidate-details/${candidateId}/`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showCandidateDetailsModal(data.candidate);
        } else {
            showToast('Failed to load candidate details', 'error');
        }
    })
    .catch(error => {
        console.error('Error loading candidate details:', error);
        showToast('Error loading candidate details', 'error');
    });
}

function editCandidate(candidateId) {
    fetch(`/api/candidate-details/${candidateId}/`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showEditCandidateModal(data.candidate);
        } else {
            showToast('Failed to load candidate details', 'error');
        }
    })
    .catch(error => {
        console.error('Error loading candidate details:', error);
        showToast('Error loading candidate details', 'error');
    });
}

function verifyCandidate(candidateId) {
    if (confirm('Are you sure you want to verify this candidate?')) {
        fetch('/api/verify-candidate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ candidate_id: candidateId }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Candidate verified successfully', 'success');
                addActivityLog(`Verified candidate: ${data.candidate_name}`);
                updateCandidateVerificationStatus(candidateId, true);
            } else {
                showToast(data.message || 'Failed to verify candidate', 'error');
            }
        })
        .catch(error => {
            showToast('Error verifying candidate', 'error');
        });
    }
}


// Helper functions for election tracking
function updateElectionStatus(electionId, newStatus) {
    const electionRow = document.querySelector(`tr[data-election-id="${electionId}"]`);
    if (electionRow) {
        const statusCell = electionRow.querySelector('.election-status');
        const statusIndicator = electionRow.querySelector('.status-indicator');
        
        if (statusCell) {
            statusCell.innerHTML = `
                <span class="status-indicator status-${newStatus}"></span>
                ${newStatus.charAt(0).toUpperCase() + newStatus.slice(1)}
            `;
        }
        
        // Update action buttons based on status
        const actionCell = electionRow.querySelector('.election-actions');
        if (actionCell) {
            updateElectionActionButtons(actionCell, electionId, newStatus);
        }
    }
}

function updateElectionActionButtons(actionCell, electionId, status) {
    let actionsHTML = `
        <div class="dropdown">
            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">
                Actions
            </button>
            <ul class="dropdown-menu">
                <li><a class="dropdown-item" href="#" onclick="monitorElection('${electionId}')">
                    <i class="fas fa-chart-line"></i> Monitor
                </a></li>
                <li><a class="dropdown-item" href="#" onclick="manageElection('${electionId}')">
                    <i class="fas fa-cog"></i> Manage
                </a></li>
                <li><a class="dropdown-item" href="#" onclick="showVotersListModal('${electionId}')">
                    <i class="fas fa-download"></i> Download Voters List
                </a></li>
    `;
    
    if (status === 'upcoming') {
        actionsHTML += `
            <li><a class="dropdown-item" href="#" onclick="startElection('${electionId}')">
                <i class="fas fa-play"></i> Start
            </a></li>
        `;
    } else if (status === 'active') {
        actionsHTML += `
            <li><a class="dropdown-item text-danger" href="#" onclick="endElection('${electionId}')">
                <i class="fas fa-stop"></i> End
            </a></li>
        `;
    }
    
    actionsHTML += `
            </ul>
        </div>
    `;
    
    actionCell.innerHTML = actionsHTML;
}

function updateElectionResults(electionId) {
    // Update the election results display if the monitoring modal is open
    const resultsContainer = document.getElementById(`election-results-${electionId}`);
    if (resultsContainer) {
        loadElectionResults(electionId, resultsContainer);
    }
}

function loadElectionResults(electionId, container) {
    fetch(`/api/election-results/${electionId}/`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            renderElectionResults(data.results, container);
        } else {
            container.innerHTML = '<p class="text-muted">No results available yet</p>';
        }
    })
    .catch(error => {
        console.error('Error loading election results:', error);
        container.innerHTML = '<p class="text-danger">Error loading results</p>';
    });
}

function renderElectionResults(results, container) {
    const totalVotes = results.reduce((sum, result) => sum + result.vote_count, 0);
    
    container.innerHTML = `
        <div class="election-results">
            <h6>Live Results (Total Votes: ${totalVotes})</h6>
            ${results.map(result => {
                const percentage = totalVotes > 0 ? ((result.vote_count / totalVotes) * 100).toFixed(1) : 0;
                return `
                    <div class="result-item mb-2">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span><strong>${result.candidate_name}</strong> (${result.party})</span>
                            <span class="badge bg-primary">${result.vote_count} votes (${percentage}%)</span>
                        </div>
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar" style="width: ${percentage}%"></div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function finalizeElectionResults(electionId) {
    fetch(`/api/finalize-election-results/${electionId}/`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addActivityLog(`Election results finalized: ${data.winner} won with ${data.winning_votes} votes`);
            showToast(`Election completed! Winner: ${data.winner}`, 'success');
        }
    })
    .catch(error => {
        console.error('Error finalizing election results:', error);
    });
}

function updateCandidateVerificationStatus(candidateId, isVerified) {
    const candidateRow = document.querySelector(`tr[data-candidate-id="${candidateId}"]`);
    if (candidateRow) {
        const verificationCell = candidateRow.querySelector('.candidate-verification');
        if (verificationCell) {
            verificationCell.innerHTML = isVerified ?
                '<span class="badge bg-success"><i class="fas fa-check"></i> Verified</span>' :
                '<span class="badge bg-warning"><i class="fas fa-clock"></i> Pending</span>';
        }
        
        // Update action buttons
        const actionButtons = candidateRow.querySelector('.candidate-actions');
        if (actionButtons && isVerified) {
            // Remove verify button
            const verifyButton = actionButtons.querySelector('.btn-outline-success');
            if (verifyButton) {
                verifyButton.remove();
            }
        }
    }
}


// Voter list download functionality
function showVotersListModal(electionId) {
    const modalHtml = `
        <div class="modal fade" id="votersListModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Download Voters List</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label for="votersListElection" class="form-label">Election</label>
                            <select class="form-select" id="votersListElection" disabled>
                                <option value="${electionId}" selected>Current Election</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="votersListState" class="form-label">State (Optional)</label>
                            <input type="text" class="form-control" id="votersListState" placeholder="Filter by state">
                        </div>
                        <div class="mb-3">
                            <label for="votersListCity" class="form-label">City (Optional)</label>
                            <input type="text" class="form-control" id="votersListCity" placeholder="Filter by city">
                        </div>
                        <div class="mb-3">
                            <label for="votersListDistrict" class="form-label">District (Optional)</label>
                            <input type="text" class="form-control" id="votersListDistrict" placeholder="Filter by district">
                        </div>
                        <div class="mb-3">
                            <label for="votersListFormat" class="form-label">Format</label>
                            <select class="form-select" id="votersListFormat">
                                <option value="csv">CSV</option>
                                <option value="excel">Excel</option>
                                <option value="pdf">PDF</option>
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="downloadVotersListByRegion()">
                            <i class="fa fa-download"></i> Download
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('votersListModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body and show
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    document.getElementById('votersListElection').value = electionId;
    
    const modal = new bootstrap.Modal(document.getElementById('votersListModal'));
    modal.show();
    
    // Remove modal from DOM when hidden
    document.getElementById('votersListModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}


function downloadVotersListByRegion() {
    const electionId = document.getElementById('votersListElection').value;
    const state = document.getElementById('votersListState').value;
    const city = document.getElementById('votersListCity').value;
    const district = document.getElementById('votersListDistrict').value;
    const format = document.getElementById('votersListFormat').value;
    
    if (!electionId) {
        showToast('Please select an election', 'warning');
        return;
    }
    
    // Build download URL with parameters
    let downloadUrl = `/api/download-voters-list/?election_id=${electionId}&format=${format}`;
    if (state) downloadUrl += `&state=${encodeURIComponent(state)}`;
    if (city) downloadUrl += `&city=${encodeURIComponent(city)}`;
    if (district) downloadUrl += `&district=${encodeURIComponent(district)}`;
    
    // Trigger download
    window.location.href = downloadUrl;
    
    // Close modal
    bootstrap.Modal.getInstance(document.getElementById('votersListModal')).hide();
    
    addActivityLog(`Downloaded voters list for election ${electionId}`);
}

// Modal functions
function showVoterDetailsModal(voter) {
    // Create and show voter details modal
    const modalHtml = `
        <div class="modal fade" id="voterDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Voter Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Voter ID:</strong> ${voter.voter_id}</p>
                                <p><strong>Name:</strong> ${voter.full_name}</p>
                                <p><strong>Email:</strong> ${voter.email}</p>
                                <p><strong>Mobile:</strong> ${voter.mobile}</p>
                                <p><strong>Date of Birth:</strong> ${voter.date_of_birth}</p>
                                <p><strong>Gender:</strong> ${voter.gender}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Address:</strong> ${voter.street_address}</p>
                                <p><strong>City:</strong> ${voter.city}</p>
                                <p><strong>State:</strong> ${voter.state}</p>
                                <p><strong>Pincode:</strong> ${voter.pincode}</p>
                                <p><strong>Status:</strong> <span class="badge bg-${voter.approval_status === 'approved' ? 'success' : voter.approval_status === 'rejected' ? 'danger' : 'warning'}">${voter.approval_status}</span></p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('voterDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body and show
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('voterDetailsModal'));
    modal.show();
    
    // Remove modal from DOM when hidden
    document.getElementById('voterDetailsModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

function showElectionMonitoringModal(electionId) {
    fetch(`/api/election-details/${electionId}/`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const election = data.election;
            
            const modalHtml = `
                <div class="modal fade" id="electionMonitorModal" tabindex="-1">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Monitor Election: ${election.name}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row">
                                    <div class="col-md-8">
                                        <div id="election-results-${electionId}">
                                            <div class="text-center">
                                                <i class="fas fa-spinner fa-spin"></i> Loading results...
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <h6>Election Info</h6>
                                        <p><strong>Type:</strong> ${election.election_type}</p>
                                        <p><strong>State:</strong> ${election.state}</p>
                                        <p><strong>Status:</strong> <span class="badge bg-${election.status === 'active' ? 'success' : election.status === 'completed' ? 'secondary' : 'warning'}">${election.status}</span></p>
                                        <p><strong>Start:</strong> ${new Date(election.start_date).toLocaleString()}</p>
                                        <p><strong>End:</strong> ${new Date(election.end_date).toLocaleString()}</p>
                                        <p><strong>Candidates:</strong> ${election.candidates_count}</p>
                                        <p><strong>Total Votes:</strong> ${election.total_votes}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal if any
            const existingModal = document.getElementById('electionMonitorModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add modal to body and show
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modal = new bootstrap.Modal(document.getElementById('electionMonitorModal'));
            modal.show();
            
            // Load election results
            loadElectionResults(electionId, document.getElementById(`election-results-${electionId}`));
            
            // Remove modal from DOM when hidden
            document.getElementById('electionMonitorModal').addEventListener('hidden.bs.modal', function() {
                this.remove();
            });
        }
    })
    .catch(error => {
        console.error('Error loading election details:', error);
        showToast('Error loading election details', 'error');
    });
}

function showElectionManagementModal(electionId) {
    // Similar to monitoring modal but with management options
    showToast('Election management panel coming soon', 'info');
}
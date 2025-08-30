// Global variables
let adminWebSocket = null;
let currentRejectVoterId = null;
let currentRejectVoterName = null;

// Initialize the admin dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    populateYearDropdown();
    setupFormHandlers();
    loadAuditLogs();
    startHeartbeat();
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
    fetch(`/api/voters/${voterId}/approve/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
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
    fetch(`/api/voters/${currentRejectVoterId}/reject/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({ reason: reason }),
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
    fetch('/api/elections/create/', {
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
    fetch('/api/candidates/add/', {
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
    
    fetch('/api/audit/logs/')
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
            <td><small class="text-muted">${log.hash.substring(0, 12)}...</small></td>
        </tr>
    `).join('');
}

// Filter audit logs
function filterAuditLogs() {
    const typeFilter = document.getElementById('logTypeFilter').value;
    const dateFilter = document.getElementById('dateFilter').value;
    
    let url = '/api/audit/logs/';
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
    
    let url = '/api/audit/logs/export/';
    const params = [];
    
    if (typeFilter) params.push(`type=${typeFilter}`);
    if (dateFilter) params.push(`date=${dateFilter}`);
    
    if (params.length > 0) {
        url += '?' + params.join('&');
    }
    
    // Trigger download
    window.location.href = url;
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
    fetch('/api/admin/stats/')
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

// Placeholder functions for various actions
function viewVoterDetails(voterId) {
    showToast('View voter details: ' + voterId, 'info');
}

function reconsiderVoter(voterId) {
    showToast('Reconsider voter: ' + voterId, 'info');
}

function monitorElection(electionId) {
    showToast('Monitor election: ' + electionId, 'info');
}

function manageElection(electionId) {
    showToast('Manage election: ' + electionId, 'info');
}

function startElection(electionId) {
    showToast('Start election: ' + electionId, 'info');
}

function endElection(electionId) {
    showToast('End election: ' + electionId, 'info');
}

function viewCandidate(candidateId) {
    showToast('View candidate: ' + candidateId, 'info');
}

function editCandidate(candidateId) {
    showToast('Edit candidate: ' + candidateId, 'info');
}

function verifyCandidate(candidateId) {
    showToast('Verify candidate: ' + candidateId, 'info');
}
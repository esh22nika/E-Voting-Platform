// Global WebSocket variable
let voterWebSocket = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeVoterWebSocket();
    setupVotingEventListeners();
});

function getCookie(name) {
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

function initializeVoterWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    voterWebSocket = new WebSocket(`${protocol}//${window.location.host}/ws/voter/`);

    voterWebSocket.onopen = (event) => console.log('Voter WebSocket connected');
    voterWebSocket.onclose = (event) => {
        console.log('Voter WebSocket disconnected');
        // Attempt to reconnect after 3 seconds
        setTimeout(initializeVoterWebSocket, 3000);
    };
    voterWebSocket.onerror = (event) => console.error('Voter WebSocket error:', event);

    voterWebSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'vote_update') {
            Swal.fire({
                title: 'Vote Verified!',
                text: `Status: ${data.data.status}. Your vote has been successfully verified and counted.`,
                icon: 'success',
                timer: 5000,
                timerProgressBar: true,
                showConfirmButton: false
            });
        }
    };
}

function setupVotingEventListeners() {
    // Add event listeners to all vote buttons
    document.querySelectorAll('.vote-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const electionId = this.getAttribute('data-election-id');
            const electionName = this.getAttribute('data-election-name');
            
            console.log('Vote button clicked for election:', electionId, electionName);
            startVoting(electionId, electionName);
        });
    });
}

// STEP 1: Show candidates in a modal when the main 'Vote' button is clicked
async function startVoting(electionId, electionName) {
    console.log('Starting voting for election:', electionId, electionName);
    
    const modal = new bootstrap.Modal(document.getElementById('votingModal'));
    const modalTitle = document.getElementById('votingModalLabel');
    const modalContent = document.getElementById('votingContent');
    
    modalTitle.innerHTML = `🗳️ Voting in: ${electionName}`;
    modalContent.innerHTML = `
        <div class="text-center p-4">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <h5>Fetching candidates...</h5>
            <p class="text-muted">Please wait while we load the candidate list.</p>
        </div>`;
    
    modal.show();
    
    try {
        const response = await fetch(`/api/candidates/${electionId}/`);
        console.log('Candidates API response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Candidates data:', data);
        
        if (data.success && data.candidates && data.candidates.length > 0) {
            const candidatesHtml = data.candidates.map(candidate => `
                <div class="card mb-3 shadow-sm candidate-card" style="transition: all 0.3s ease;">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-md-8">
                                <h5 class="card-title mb-1 text-primary">${candidate.name}</h5>
                                <p class="card-text text-muted mb-2">
                                    <i class="fas fa-flag"></i> ${candidate.party}
                                </p>
                                ${candidate.symbol ? `<small class="text-muted">Symbol: ${candidate.symbol}</small>` : ''}
                            </div>
                            <div class="col-md-4 text-end">
                                <button class="btn btn-success btn-lg candidate-vote-btn" 
                                        data-election-id="${electionId}" 
                                        data-candidate-id="${candidate.id}" 
                                        data-candidate-name="${candidate.name.replace(/'/g, "&#39;")}"
                                        style="min-width: 120px;">
                                    <i class="fas fa-vote-yea"></i> Vote
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
            
            modalContent.innerHTML = `
                <div class="text-center mb-4">
                    <h4 class="text-primary">Select Your Candidate</h4>
                    <p class="text-muted">Choose the candidate you want to vote for. This action cannot be undone.</p>
                    <hr>
                </div>
                ${candidatesHtml}
            `;

            // Add event listeners to candidate vote buttons
            modalContent.querySelectorAll('.candidate-vote-btn').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const electionId = this.getAttribute('data-election-id');
                    const candidateId = this.getAttribute('data-candidate-id');
                    const candidateName = this.getAttribute('data-candidate-name');
                    
                    console.log('Candidate vote button clicked:', candidateId, candidateName);
                    confirmVote(electionId, candidateId, candidateName);
                });
            });

        } else {
            modalContent.innerHTML = `
                <div class="alert alert-warning text-center">
                    <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                    <h5>No Candidates Found</h5>
                    <p>${data.message || 'No candidates are available for this election at the moment.'}</p>
                </div>`;
        }
    } catch (error) {
        console.error('Failed to fetch candidates:', error);
        modalContent.innerHTML = `
            <div class="alert alert-danger text-center">
                <i class="fas fa-exclamation-circle fa-2x mb-3"></i>
                <h5>Error Loading Candidates</h5>
                <p>An error occurred while loading candidates. Please check your connection and try again.</p>
                <button class="btn btn-outline-danger" onclick="startVoting('${electionId}', '${electionName}')">
                    <i class="fas fa-redo"></i> Retry
                </button>
            </div>`;
    }
}

// STEP 2: Show a confirmation popup when a specific candidate's vote button is clicked
function confirmVote(electionId, candidateId, candidateName) {
    console.log('Confirming vote for:', candidateId, candidateName);
    
    Swal.fire({
        title: 'Confirm Your Vote',
        html: `
            <div class="text-center">
                <i class="fas fa-vote-yea fa-3x text-success mb-3"></i>
                <h5>Are you sure you want to vote for</h5>
                <h4 class="text-primary">${candidateName}?</h4>
                <div class="alert alert-warning mt-3">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>Important:</strong> This action cannot be undone!
                </div>
            </div>
        `,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#198754',
        cancelButtonColor: '#6c757d',
        confirmButtonText: '<i class="fas fa-check"></i> Yes, Cast My Vote!',
        cancelButtonText: '<i class="fas fa-times"></i> Cancel',
        reverseButtons: true,
        customClass: {
            confirmButton: 'btn btn-success btn-lg me-2',
            cancelButton: 'btn btn-secondary btn-lg'
        },
        buttonsStyling: false
    }).then((result) => {
        if (result.isConfirmed) {
            castVote(electionId, candidateId, candidateName);
        }
    });
}

// STEP 3: Cast the vote and update the UI
async function castVote(electionId, candidateId, candidateName) {
    console.log('Casting vote for:', candidateId, candidateName);
    
    // Close the candidate selection modal first
    const modal = bootstrap.Modal.getInstance(document.getElementById('votingModal'));
    if(modal) modal.hide();

    // Show loading popup
    Swal.fire({
        title: 'Casting Your Vote...',
        html: `
            <div class="text-center">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p>Please wait while we process your vote for <strong>${candidateName}</strong></p>
            </div>
        `,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    try {
        const response = await fetch('/api/cast-vote/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ 
                election_id: electionId, 
                candidate_id: candidateId 
            })
        });

        console.log('Cast vote response status:', response.status);
        const result = await response.json();
        console.log('Cast vote result:', result);
        
        if (result.success) {
            // Show success popup
            await Swal.fire({
                title: 'Vote Cast Successfully! 🎉',
                html: `
                    <div class="text-center">
                        <i class="fas fa-check-circle fa-4x text-success mb-3"></i>
                        <h5 class="text-success">Your vote has been recorded!</h5>
                        <p class="text-muted">${result.message}</p>
                        <div class="alert alert-info mt-3">
                            <i class="fas fa-info-circle"></i>
                            Your vote is being processed and will be verified shortly.
                        </div>
                    </div>
                `,
                icon: 'success',
                confirmButtonText: '<i class="fas fa-thumbs-up"></i> Great!',
                confirmButtonColor: '#198754',
                timer: 5000,
                timerProgressBar: true
            });

            // Update the UI on the main page to show 'Voted' status with animation
            const electionActionsDiv = document.getElementById(`election-actions-${electionId}`);
            if (electionActionsDiv) {
                electionActionsDiv.innerHTML = `
                    <div class="d-flex justify-content-end align-items-center voted-container" style="opacity: 0;">
                        <span class="text-success fw-bold me-2">✅ Voted</span>
                        <button class="btn btn-outline-secondary btn-sm" disabled>
                            <i class="fas fa-check"></i> Vote Cast
                        </button>
                    </div>
                `;
                
                // Animate the appearance
                setTimeout(() => {
                    electionActionsDiv.querySelector('.voted-container').style.cssText = 
                        'opacity: 1; animation: voteSuccess 0.8s ease-in-out;';
                }, 100);
            }
            
            // Update the 'Votes Cast' counter with animation
            const votesCounter = document.getElementById('votesCastedCount');
            if (votesCounter) {
                let currentCount = parseInt(votesCounter.textContent) || 0;
                votesCounter.style.animation = 'counterUpdate 0.5s ease-in-out';
                setTimeout(() => {
                    votesCounter.textContent = currentCount + 1;
                    votesCounter.style.animation = '';
                }, 250);
            }
            
        } else {
            Swal.fire({
                title: 'Vote Failed',
                html: `
                    <div class="text-center">
                        <i class="fas fa-times-circle fa-3x text-danger mb-3"></i>
                        <p>${result.message || 'An error occurred while casting your vote.'}</p>
                    </div>
                `,
                icon: 'error',
                confirmButtonText: '<i class="fas fa-redo"></i> Try Again',
                confirmButtonColor: '#dc3545'
            });
        }
    } catch (error) {
        console.error('Error casting vote:', error);
        Swal.fire({
            title: 'Network Error',
            html: `
                <div class="text-center">
                    <i class="fas fa-wifi fa-3x text-danger mb-3"></i>
                    <h5>Connection Error</h5>
                    <p>Failed to cast your vote due to a network error. Please check your internet connection and try again.</p>
                </div>
            `,
            icon: 'error',
            confirmButtonText: '<i class="fas fa-redo"></i> Retry',
            confirmButtonColor: '#dc3545'
        });
    }
}
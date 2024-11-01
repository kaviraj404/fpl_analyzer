document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysis-form');
    const results = document.getElementById('results');
    const loading = document.getElementById('loading');
    const errorMessage = document.getElementById('error-message');
    const teamIdInput = document.getElementById('team-id');
    const analyzeButton = document.getElementById('analyze-button');

    // Initialize modals
    const modal = document.getElementById('playerModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closePlayerModal();
            }
        });
    }

    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    async function handleFormSubmit(e) {
        e.preventDefault();
        
        analyzeButton.disabled = true;
        analyzeButton.innerHTML = 'Analyzing...';
        
        errorMessage.classList.add('hidden');
        loading.classList.remove('hidden');
        results.classList.add('hidden');

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ team_id: teamIdInput.value })
            });

            const data = await response.json();
            console.log('Received data:', data);

            if (!data.success) {
                throw new Error(data.error || 'Analysis failed');
            }

            displayResults(data);
            results.classList.remove('hidden');
            
        } catch (error) {
            console.error('Error:', error);
            showError(error.message);
        } finally {
            analyzeButton.disabled = false;
            analyzeButton.innerHTML = 'Analyze';
            loading.classList.add('hidden');
        }
    }

    function displayResults(data) {
        results.innerHTML = `
            <!-- Team Status -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                <h3 class="text-lg font-semibold mb-4 text-blue-800">
                    <i class="fas fa-shield-alt mr-2"></i>Team Status
                </h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="stat-item">
                        <p class="stat-label">Team Name</p>
                        <p class="stat-value">${data.team_status.name}</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Overall Points</p>
                        <p class="stat-value">${data.team_status.overall_points}</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Overall Rank</p>
                        <p class="stat-value">${data.team_status.overall_rank.toLocaleString()}</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Bank Balance</p>
                        <p class="stat-value">£${data.team_status.bank_balance.toFixed(1)}m</p>
                    </div>
                </div>
            </div>

            <!-- Captain Picks -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                <h3 class="text-lg font-semibold mb-4 text-blue-800">
                    <i class="fas fa-star mr-2"></i>Captain Recommendations
                </h3>
                <div class="space-y-4">
                    ${data.captain_picks.map((pick, index) => `
                        <div class="player-card p-4 bg-gray-50 rounded-lg hover:shadow-md transition-all cursor-pointer"
                             onclick="showPlayerDetails(${pick.player_id})">
                            <div class="flex justify-between items-center">
                                <div>
                                    <p class="font-semibold text-lg">
                                        ${pick.name}
                                        ${index === 0 ? 
                                            '<span class="ml-2 bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm">👑 Captain</span>' : 
                                            index === 1 ? 
                                            '<span class="ml-2 bg-gray-100 text-gray-800 px-2 py-1 rounded-full text-sm">🥈 Vice</span>' : 
                                            ''}
                                    </p>
                                    <p class="text-gray-600">${pick.team} - ${pick.position}</p>
                                </div>
                                <div class="text-right">
                                    <p class="font-semibold text-blue-600">${pick.predicted_points.toFixed(1)} pts</p>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Transfer Suggestions -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                        <h3 class="text-lg font-semibold mb-4 text-blue-800">
                            <i class="fas fa-exchange-alt mr-2"></i>Transfer Suggestions
                        </h3>
                        <div class="space-y-6">
                            ${data.transfer_suggestions.map((transfer, index) => `
                                <div class="bg-gray-50 rounded-lg p-4">
                                    <div class="flex items-center gap-4">
                                        <!-- Player Out -->
                                        <div class="flex-1 bg-red-50 p-4 rounded-lg cursor-pointer hover:shadow-md transition-all"
                                            onclick="showPlayerDetails(${transfer.out.player_id})">
                                            <p class="font-semibold text-red-600 mb-1">Transfer Out</p>
                                            <div class="space-y-1">
                                                <p class="font-medium">${transfer.out.name}</p>
                                                <p class="text-sm text-gray-600">Form: ${Number(transfer.out.form).toFixed(1)}</p>
                                                <p class="text-sm text-gray-600">Predicted Points: ${Math.round(transfer.out.predicted_points)}</p>
                                            </div>
                                        </div>

                                        <!-- Arrow and Stats -->
                                        <div class="flex flex-col items-center px-2">
                                            <span class="text-2xl text-gray-400 mb-2">→</span>
                                            <div class="text-center bg-white rounded-lg p-2 shadow-sm">
                                                <p class="text-sm font-medium text-blue-600">+${Math.round(transfer.improvement)} pts</p>
                                                <p class="text-xs text-gray-500">predicted gain</p>
                                            </div>
                                        </div>

                                        <!-- Player In -->
                                        <div class="flex-1 bg-green-50 p-4 rounded-lg cursor-pointer hover:shadow-md transition-all"
                                            onclick="showPlayerDetails(${transfer.in.player_id})">
                                            <p class="font-semibold text-green-600 mb-1">Transfer In</p>
                                            <div class="space-y-1">
                                                <p class="font-medium">${transfer.in.name}</p>
                                                <p class="text-sm text-gray-600">Form: ${Number(transfer.in.form).toFixed(1)}</p>
                                                <p class="text-sm text-gray-600">Predicted Points: ${Math.round(transfer.in.predicted_points)}</p>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <!-- Transfer Summary -->
                                    <div class="mt-3 pt-3 border-t border-gray-200 text-sm text-gray-600 flex justify-between">
                                        <span>Price Change: ${Number(transfer.price_change).toFixed(1)}m</span>
                                        <span>Budget After: £${Number(transfer.remaining_budget).toFixed(1)}</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

            <!-- Current Squad -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                        <h3 class="text-lg font-semibold mb-4 text-blue-800">
                            <i class="fas fa-users mr-2"></i>Current Squad
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            ${data.current_squad.map(player => `
                                <div class="player-card p-4 bg-gray-50 rounded-lg hover:shadow-md transition-all cursor-pointer"
                                    onclick="showPlayerDetails(${player.player_id})">
                                    <div class="flex justify-between items-center">
                                        <div>
                                            <p class="font-semibold">${player.name}</p>
                                            <p class="text-sm text-gray-600">${player.team} - ${player.position}</p>
                                        </div>
                                        <div class="text-right">
                                            <p class="text-sm">£${player.price}m</p>
                                            <p class="text-sm">Form: ${player.form}</p>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

            <!-- Info Section -->
            <div class="bg-blue-50 border-l-4 border-blue-400 p-4">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <i class="fas fa-info-circle text-blue-400"></i>
                    </div>
                    <div class="ml-3">
                        <p class="text-sm text-blue-700">
                            Want to understand how we calculate predicted points?
                            <a href="/methodology" class="underline font-semibold">Learn about our methodology</a>
                        </p>
                    </div>
                </div>
            </div>
        `;
    }

    function showError(message) {
        const errorText = errorMessage.querySelector('p');
        errorText.textContent = message;
        errorMessage.classList.remove('hidden');
    }
});

async function showPlayerDetails(playerId) {
    console.log('ShowPlayerDetails called with ID:', playerId);
    
    if (!playerId) {
        console.error('No player ID provided');
        return;
    }
    
    try {
        const response = await fetch(`/player/${playerId}`);  // Using the correct player ID
        if (!response.ok) {
            throw new Error(`Failed to fetch player details. Status: ${response.status}`);
        }
        const player = await response.json();
        
        const modal = document.getElementById('playerModal');
        const content = document.getElementById('modalContent');
        
        content.innerHTML = `
            <div class="space-y-4">
                <div class="flex justify-between items-center">
                    <div>
                        <h4 class="text-xl font-bold">${player.name}</h4>
                        <p class="text-gray-600">${player.team} - ${player.position}</p>
                    </div>
                    <p class="text-xl font-bold">£${player.price.toFixed(1)}m</p>
                </div>

                <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div class="stat-item">
                        <p class="stat-label">Total Points</p>
                        <p class="stat-value">${player.total_points}</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Form</p>
                        <p class="stat-value">${player.form}</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Points Per Game</p>
                        <p class="stat-value">${player.points_per_game}</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Minutes Per Game</p>
                        <p class="stat-value">${player.minutes_per_game}</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Games Played</p>
                        <p class="stat-value">${player.games_played}</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Selected By</p>
                        <p class="stat-value">${player.selected_by}%</p>
                    </div>
                    <div class="stat-item">
                        <p class="stat-label">Predicted Points</p>
                        <p class="stat-value">${player.predicted_points ? player.predicted_points.toFixed(1) : '0.0'}</p>
                    </div>
                </div>

                <div class="mt-6">
                    <h5 class="font-semibold mb-3">Recent Performance</h5>
                    <canvas id="playerPerformanceChart"></canvas>
                </div>
            </div>
        `;

        modal.classList.remove('hidden');
        modal.classList.add('flex');
        
        const ctx = document.getElementById('playerPerformanceChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['GW-4', 'GW-3', 'GW-2', 'GW-1', 'Last GW'],
                datasets: [{
                    label: 'Points',
                    data: player.recent_performance.points.reverse(),
                    borderColor: 'rgb(59, 130, 246)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Last 5 Gameweeks Performance'
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error fetching player details:', error);
    }
}

function closePlayerModal() {
    const modal = document.getElementById('playerModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// Close modal when clicking outside
document.getElementById('playerModal')?.addEventListener('click', function(e) {
    if (e.target === this) {
        closePlayerModal();
    }
});
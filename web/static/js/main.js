document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysis-form');
    const results = document.getElementById('results');
    const loading = document.getElementById('loading');
    const errorMessage = document.getElementById('error-message');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Reset UI
        errorMessage.classList.add('hidden');
        loading.classList.remove('hidden');
        results.classList.add('hidden');

        const teamId = document.getElementById('team-id').value;

        try {
            if (!teamId || teamId < 1) {
                throw new Error('Please enter a valid team ID');
            }

            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ team_id: teamId })
            });

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Analysis failed');
            }

            // Display results
            // In the displayResults section of main.js:

            results.innerHTML = `
                <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                    <h3 class="text-lg font-semibold mb-3">Team Status</h3>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="stat-item">
                            <p class="stat-label">Team Name</p>
                            <p class="stat-value">${data.team_status.name || 'N/A'}</p>
                        </div>
                        <div class="stat-item">
                            <p class="stat-label">Overall Points</p>
                            <p class="stat-value">${data.team_status.overall_points || '0'}</p>
                        </div>
                        <div class="stat-item">
                            <p class="stat-label">Overall Rank</p>
                            <p class="stat-value">${(data.team_status.overall_rank || 0).toLocaleString()}</p>
                        </div>
                        <div class="stat-item">
                            <p class="stat-label">Bank Balance</p>
                            <p class="stat-value">£${data.team_status.bank_balance ? data.team_status.bank_balance.toFixed(1) : '0.0'}m</p>
                        </div>
                    </div>
                </div>

                <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                    <h3 class="text-lg font-semibold mb-3">Current Squad</h3>
                    <div class="grid gap-4">
                        ${data.current_squad.map(player => `
                            <div class="player-card">
                                <div class="flex justify-between items-center">
                                    <div>
                                        <p class="font-semibold">${player.name || 'Unknown'}</p>
                                        <p class="text-sm text-gray-600">${player.team || 'N/A'} - ${player.position || 'N/A'}</p>
                                    </div>
                                    <div class="text-right">
                                        <p class="text-sm">£${player.price ? player.price.toFixed(1) : '0.0'}m</p>
                                        <p class="text-sm">Form: ${player.form || '0.0'}</p>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                    <h3 class="text-lg font-semibold mb-3">Captain Picks</h3>
                    ${data.captain_picks.map((pick, index) => `
                        <div class="player-card">
                            <div class="flex justify-between items-center">
                                <div>
                                    <p class="font-semibold">
                                        ${pick.name || 'Unknown'} (${pick.position || 'N/A'})
                                        ${index === 0 ? '<span class="captain-badge">👑 Captain</span>' : 
                                        index === 1 ? '<span class="vice-captain-badge">🥈 Vice Captain</span>' : ''}
                                    </p>
                                    <p class="text-sm text-gray-600">
                                        ${pick.is_home ? 'HOME' : 'AWAY'} vs ${pick.opponent || 'N/A'}
                                    </p>
                                    <p class="text-sm text-gray-600">
                                        Predicted Points: ${pick.predicted_points ? pick.predicted_points.toFixed(1) : '0.0'} | Form: ${pick.form || '0.0'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>

                <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                    <h3 class="text-lg font-semibold mb-3">Transfer Suggestions</h3>
                    ${data.transfer_suggestions.map((transfer, index) => `
                        <div class="mb-6 last:mb-0">
                            <div class="flex items-center mb-2">
                                <div class="flex-1 bg-red-50 p-3 rounded-lg">
                                    <p class="font-semibold text-red-600">OUT: ${transfer.out.name || 'Unknown'}</p>
                                    <p class="text-sm text-gray-600">Team: ${transfer.out.team || 'N/A'}</p>
                                    <p class="text-sm text-gray-600">Form: ${transfer.out.form || '0.0'}</p>
                                </div>
                                <div class="mx-4 transfer-arrow">→</div>
                                <div class="flex-1 bg-green-50 p-3 rounded-lg">
                                    <p class="font-semibold text-green-600">IN: ${transfer.in.name || 'Unknown'}</p>
                                    <p class="text-sm text-gray-600">Team: ${transfer.in.team || 'N/A'}</p>
                                    <p class="text-sm text-gray-600">Form: ${transfer.in.form || '0.0'}</p>
                                </div>
                            </div>
                            <div class="bg-gray-50 rounded p-3">
                                <p class="text-sm">Price Change: £${transfer.price_diff ? transfer.price_diff.toFixed(1) : '0.0'}m</p>
                                <p class="text-sm">Remaining Budget: £${transfer.remaining_budget ? transfer.remaining_budget.toFixed(1) : '0.0'}m</p>
                                <p class="text-sm">Expected Point Gain: ${transfer.predicted_point_gain ? transfer.predicted_point_gain.toFixed(1) : '0.0'}</p>
                                ${transfer.in.selected_by < 10 ? 
                                    `<p class="text-sm text-blue-600 mt-1">
                                        Differential Pick (${transfer.in.selected_by || '0'}% ownership)
                                    </p>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>

                ${data.considerations.inactive_players || data.considerations.out_of_form_players ? `
                    <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                        <div class="flex">
                            <div class="flex-shrink-0">
                                ⚠️
                            </div>
                            <div class="ml-3">
                                <h3 class="text-sm font-medium text-yellow-800">Considerations</h3>
                                <div class="mt-2 text-sm text-yellow-700">
                                    ${data.considerations.inactive_players ? 
                                        '<p>• You have inactive players that might need attention</p>' : ''}
                                    ${data.considerations.out_of_form_players ? 
                                        '<p>• Some players in your squad are out of form</p>' : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                ` : ''}
                `;
            results.classList.remove('hidden');
        } catch (error) {
            errorMessage.querySelector('p').textContent = error.message;
            errorMessage.classList.remove('hidden');
            results.classList.add('hidden');
        } finally {
            loading.classList.add('hidden');
        }
    });
});
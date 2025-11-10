/**
 * Real-time Tournament Prize Calculator for Django Admin
 * Calculates prize pool and distribution as admin enters data
 */

(function() {
    'use strict';

    // Prize distribution percentages based on best_of count
    const PRIZE_DISTRIBUTIONS = {
        1: [[1, 100]],
        2: [[1, 60], [2, 40]],
        3: [[1, 50], [2, 30], [3, 20]],
        4: [[1, 40], [2, 30], [3, 20], [4, 10]],
        5: [[1, 40], [2, 25], [3, 15], [4, 12], [5, 8]],
        6: [[1, 35], [2, 25], [3, 15], [4, 12], [5, 8], [6, 5]],
        7: [[1, 35], [2, 22], [3, 15], [4, 11], [5, 8], [6, 5], [7, 4]],
        8: [[1, 35], [2, 20], [3, 13], [4, 10], [5, 8], [6, 6], [7, 4], [8, 4]],
    };

    const MEDALS = {
        1: '🥇',
        2: '🥈',
        3: '🥉'
    };

    // Format number with Persian thousand separators
    function formatNumber(num) {
        return Math.floor(num).toLocaleString('en-US').replace(/,/g, '،');
    }

    // Get prize distribution for given best_of value
    function getPrizeDistribution(bestOf) {
        if (bestOf in PRIZE_DISTRIBUTIONS) {
            return PRIZE_DISTRIBUTIONS[bestOf];
        }
        // For values > 8, distribute equally
        const distribution = [];
        const percentage = 100 / bestOf;
        for (let i = 1; i <= bestOf; i++) {
            distribution.push([i, percentage]);
        }
        return distribution;
    }

    // Calculate and update all prize displays
    function updatePrizeCalculations() {
        // Get input values
        const entryFee = parseFloat(document.getElementById('id_entry_fee')?.value) || 0;
        const maxParticipants = parseInt(document.getElementById('id_max_participants')?.value) || 0;
        const commission = parseFloat(document.getElementById('id_platform_commission')?.value) || 0;
        const bestOf = parseInt(document.getElementById('id_best_of')?.value) || 1;

        // Validate inputs
        if (!entryFee || !maxParticipants) {
            return;
        }

        // Calculate totals
        const totalPrizePool = entryFee * maxParticipants;
        const commissionAmount = (totalPrizePool * commission) / 100;
        const prizeAfterCommission = totalPrizePool - commissionAmount;

        // Update calculated prize pool
        updatePrizePoolDisplay(totalPrizePool);

        // Update prize after commission
        updatePrizeAfterCommissionDisplay(prizeAfterCommission, commissionAmount);

        // Update prize distribution
        updatePrizeDistributionDisplay(prizeAfterCommission, bestOf);
    }

    // Update total prize pool display
    function updatePrizePoolDisplay(total) {
        const container = document.getElementById('calc_prize_pool');
        if (container) {
            container.innerHTML = `
                <strong style="color: #2e7d32; font-size: 16px;">💰 ${formatNumber(total)} تومان</strong>
                <br><small style="color: #666;">جایزه کل محاسبه شده</small>
            `;
        }
    }

    // Update prize after commission display
    function updatePrizeAfterCommissionDisplay(afterCommission, commissionAmount) {
        const container = document.getElementById('calc_after_commission');
        if (container) {
            container.innerHTML = `
                <strong style="color: #1565c0; font-size: 16px;">💵 ${formatNumber(afterCommission)} تومان</strong>
                <br><small style="color: #666;">پس از کسر کمیسیون (${formatNumber(commissionAmount)} تومان)</small>
            `;
        }
    }

    // Update prize distribution display
    function updatePrizeDistributionDisplay(totalAfterCommission, bestOf) {
        const container = document.getElementById('calc_distribution');
        if (!container) return;

        const distribution = getPrizeDistribution(bestOf);

        let html = '<strong style="color: #e65100; font-size: 14px;">🏆 توزیع جوایز نفرات برتر:</strong><br><br>';

        distribution.forEach(([rank, percentage]) => {
            const prizeAmount = (totalAfterCommission * percentage) / 100;
            const medal = MEDALS[rank] || '🏅';

            html += `
                <div style="margin: 5px 0; padding: 5px; background: white; border-radius: 3px;">
                    <strong>${medal} نفر ${rank}: </strong>
                    <span style="color: #2e7d32; font-weight: bold;">${formatNumber(prizeAmount)} تومان</span>
                    <small style="color: #666;">(${Math.round(percentage)}%)</small>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    // Initialize calculator when DOM is ready
    function initCalculator() {
        // Wait for Django admin to be fully loaded
        if (typeof django === 'undefined' || !document.getElementById('id_entry_fee')) {
            setTimeout(initCalculator, 100);
            return;
        }

        // Get all relevant input fields
        const entryFeeInput = document.getElementById('id_entry_fee');
        const maxParticipantsInput = document.getElementById('id_max_participants');
        const commissionInput = document.getElementById('id_platform_commission');
        const bestOfInput = document.getElementById('id_best_of');

        // Add event listeners
        if (entryFeeInput) {
            entryFeeInput.addEventListener('input', updatePrizeCalculations);
            entryFeeInput.addEventListener('change', updatePrizeCalculations);
        }
        if (maxParticipantsInput) {
            maxParticipantsInput.addEventListener('input', updatePrizeCalculations);
            maxParticipantsInput.addEventListener('change', updatePrizeCalculations);
        }
        if (commissionInput) {
            commissionInput.addEventListener('input', updatePrizeCalculations);
            commissionInput.addEventListener('change', updatePrizeCalculations);
        }
        if (bestOfInput) {
            bestOfInput.addEventListener('input', updatePrizeCalculations);
            bestOfInput.addEventListener('change', updatePrizeCalculations);
        }

        // Initial calculation
        updatePrizeCalculations();
    }

    // Start initialization when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCalculator);
    } else {
        initCalculator();
    }
})();

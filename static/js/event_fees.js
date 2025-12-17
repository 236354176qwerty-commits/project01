/**
 * 赛事费用管理 - localStorage版本
 */

/**
 * 保存赛事费用数据到localStorage
 * @param {number} eventId - 赛事ID
 * @param {object} feeData - 费用数据对象
 */
function saveEventFees(eventId, feeData) {
    try {
        const eventFees = JSON.parse(localStorage.getItem('eventFees') || '{}');
        
        eventFees[eventId] = {
            individual_fee: feeData.individual_fee || 0,
            pair_practice_fee: feeData.pair_practice_fee || 0,
            team_competition_fee: feeData.team_competition_fee || 0
        };
        
        localStorage.setItem('eventFees', JSON.stringify(eventFees));
        
        console.log(`已保存赛事 ${eventId} 的费用数据:`, eventFees[eventId]);
    } catch (error) {
        console.error('保存赛事费用失败:', error);
    }
}

/**
 * 从localStorage获取赛事费用数据
 * @param {number} eventId - 赛事ID
 * @returns {object} 费用数据对象
 */
function getEventFees(eventId) {
    try {
        const eventFees = JSON.parse(localStorage.getItem('eventFees') || '{}');
        return eventFees[eventId] || {
            individual_fee: 0,
            pair_practice_fee: 0,
            team_competition_fee: 0
        };
    } catch (error) {
        console.error('读取赛事费用失败:', error);
        return {
            individual_fee: 0,
            pair_practice_fee: 0,
            team_competition_fee: 0
        };
    }
}

/**
 * 增强event对象，添加费用数据
 * @param {object} event - 赛事对象
 * @returns {object} 增强后的赛事对象
 */
function enhanceEventWithFees(event) {
    if (!event || !event.event_id) return event;
    
    const fees = getEventFees(event.event_id);
    return {
        ...event,
        individual_fee: fees.individual_fee,
        pair_practice_fee: fees.pair_practice_fee,
        team_competition_fee: fees.team_competition_fee
    };
}

/**
 * 批量增强event对象数组
 * @param {array} events - 赛事对象数组
 * @returns {array} 增强后的赛事对象数组
 */
function enhanceEventsWithFees(events) {
    if (!Array.isArray(events)) return events;
    return events.map(event => enhanceEventWithFees(event));
}

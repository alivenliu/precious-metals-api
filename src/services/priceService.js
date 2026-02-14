const axios = require('axios');
const NodeCache = require('node-cache');

const cache = new NodeCache({ stdTTL: process.env.CACHE_TTL || 60 });

/**
 * 从 Twelve Data 获取价格
 */
const fetchFromTwelveData = async (symbols) => {
    const apiKey = process.env.TWELVE_DATA_KEY;
    const url = `https://api.twelvedata.com/price?symbol=${symbols}&apikey=${apiKey}`;
    const response = await axios.get(url);
    return response.data;
};

/**
 * 获取最新价格
 * 针对免费版限制，我们尝试获取尽可能多的品种
 */
const getLatestPrices = async (symbols) => {
    // 默认请求的品种
    const defaultSymbols = 'XAU/USD,USD/CNY,USD/CNH,USD/HKD,EUR/USD';
    const targetSymbols = symbols || defaultSymbols;
    
    const cacheKey = `prices_${targetSymbols}`;
    const cachedData = cache.get(cacheKey);
    if (cachedData) return cachedData;

    try {
        const data = await fetchFromTwelveData(targetSymbols);
        
        // 格式化输出，处理可能的部分错误
        const rates = {};
        if (targetSymbols.includes(',')) {
            for (const [key, value] of Object.entries(data)) {
                if (value.status === 'error') {
                    rates[key] = { error: value.message };
                } else {
                    rates[key] = value;
                }
            }
        } else {
            if (data.status === 'error') {
                rates[targetSymbols] = { error: data.message };
            } else {
                rates[targetSymbols] = data;
            }
        }

        const formattedData = {
            source: 'Twelve Data',
            timestamp: new Date().toISOString(),
            rates: rates,
            note: 'Some symbols (like XAG, XPT, XPD) might require a paid Twelve Data plan. For full metals support, consider adding a GoldAPI.io key.'
        };

        cache.set(cacheKey, formattedData);
        return formattedData;
    } catch (error) {
        throw new Error(`Price fetch failed: ${error.message}`);
    }
};

module.exports = { getLatestPrices };

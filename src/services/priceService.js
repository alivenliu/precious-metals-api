const axios = require('axios');
const NodeCache = require('node-cache');

// 缓存设置：默认 60 秒过期
const cache = new NodeCache({ stdTTL: process.env.CACHE_TTL || 60 });

const getLatestPrices = async (symbols = 'XAU,XAG,EUR/USD,GBP/USD') => {
    const cacheKey = `prices_${symbols}`;
    const cachedData = cache.get(cacheKey);
    
    if (cachedData) {
        console.log('Returning cached data');
        return cachedData;
    }

    try {
        // 这里以 Twelve Data 为例，因为它同时支持外汇和金属
        // 金属符号通常是 XAU/USD, XAG/USD
        const apiKey = process.env.TWELVE_DATA_KEY;
        const url = `https://api.twelvedata.com/price?symbol=${symbols}&apikey=${apiKey}`;
        
        const response = await axios.get(url);
        const data = response.data;

        // 格式化输出
        const formattedData = {
            source: 'Twelve Data',
            timestamp: new Date().toISOString(),
            rates: data
        };

        cache.set(cacheKey, formattedData);
        return formattedData;
    } catch (error) {
        console.error('Error fetching prices:', error.message);
        throw new Error('Failed to fetch price data');
    }
};

module.exports = {
    getLatestPrices
};

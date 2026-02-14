const axios = require('axios');
const NodeCache = require('node-cache');

const cache = new NodeCache({ stdTTL: process.env.CACHE_TTL || 60 });

const fetchFromTwelveData = async (symbols) => {
    const apiKey = process.env.TWELVE_DATA_KEY;
    const url = `https://api.twelvedata.com/price?symbol=${symbols}&apikey=${apiKey}`;
    const response = await axios.get(url);
    return response.data;
};

const getLatestPrices = async (customSymbols) => {
    // 默认请求的品种：包含黄金、外汇以及用于换算的 EUR 交叉盘
    const baseSymbols = 'XAU/USD,XAG/EUR,XPT/EUR,XPD/EUR,EUR/USD,USD/CNY,USD/CNH,USD/HKD';
    const symbolsToFetch = customSymbols || baseSymbols;
    
    const cacheKey = `prices_v4_${symbolsToFetch}`;
    const cachedData = cache.get(cacheKey);
    if (cachedData) return cachedData;

    try {
        const rawData = await fetchFromTwelveData(symbolsToFetch);
        
        // 处理 API 级错误 (如 429)
        if (rawData.status === 'error' && rawData.code === 429) {
            throw new Error('API Rate Limit exceeded. Please try again in a minute.');
        }

        const rates = {};
        const getPrice = (sym) => {
            const item = rawData[sym];
            return (item && item.status !== 'error') ? parseFloat(item.price) : null;
        };

        const eurUsd = getPrice('EUR/USD');

        // 1. 填充原始数据
        if (symbolsToFetch.includes(',')) {
            for (const [symbol, info] of Object.entries(rawData)) {
                if (info.status === 'error') {
                    rates[symbol] = { error: info.message };
                } else {
                    rates[symbol] = info;
                }
            }
        } else {
            rates[symbolsToFetch] = rawData.status === 'error' ? { error: rawData.message } : rawData;
        }

        // 2. 执行交叉盘换算 (X / EUR * EUR / USD = X / USD)
        const crossPairs = [
            { from: 'XAG/EUR', to: 'XAG/USD' },
            { from: 'XPT/EUR', to: 'XPT/USD' },
            { from: 'XPD/EUR', to: 'XPD/USD' }
        ];

        if (eurUsd) {
            crossPairs.forEach(pair => {
                const priceInEur = getPrice(pair.from);
                if (priceInEur) {
                    const priceInUsd = (priceInEur * eurUsd).toFixed(5);
                    rates[pair.to] = {
                        price: priceInUsd,
                        calculated: true,
                        via: `(${pair.from} * EUR/USD)`
                    };
                }
            });
        }

        const formattedData = {
            source: 'Twelve Data (with Cross-Rate Calculation)',
            timestamp: new Date().toISOString(),
            rates: rates,
            note: 'XAG, XPT, XPD prices are calculated via EUR cross-rates to bypass free tier limitations.'
        };

        cache.set(cacheKey, formattedData);
        return formattedData;
    } catch (error) {
        throw new Error(`Price fetch failed: ${error.message}`);
    }
};

module.exports = { getLatestPrices };

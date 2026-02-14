require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { getLatestPrices } = require('./services/priceService');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// 根路由
app.get('/', (req, res) => {
    res.json({
        message: 'Real-time Precious Metals & Forex API (Updated)',
        default_symbols: [
            'XAU/USD (Gold)', 
            'XAG/USD (Silver)', 
            'XPT/USD (Platinum)', 
            'XPD/USD (Palladium)', 
            'USD/CNY', 
            'USD/CNH', 
            'USD/HKD'
        ],
        endpoints: {
            latest: '/api/latest',
            custom: '/api/latest?symbols=XAU/USD,USD/CNY',
            health: '/health'
        }
    });
});

// 获取最新价格
app.get('/api/latest', async (req, res) => {
    const { symbols } = req.query;
    try {
        // 如果没有传 symbols，getLatestPrices 会使用内部定义的默认值
        const prices = await getLatestPrices(symbols);
        res.json(prices);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 健康检查
app.get('/health', (req, res) => {
    res.json({ status: 'UP', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});

const express = require('express');
const authRouter = require('./auth');
const app = express();

app.use(express.json());

app.use('/auth', authRouter);

app.get('/health', (req, res) => {
    res.status(200).json({ status: 'ok' });
});

module.exports = app;
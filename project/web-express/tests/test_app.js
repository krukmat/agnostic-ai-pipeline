const express = require('express');
const app = express();
app.get('/health', (req, res) => {
    res.json({status: 'ok'});
});
describe('Health Check', () => {
    it('should return status ok', async () => {
        const response = await request(app).get('/health');
        expect(response.status).toBe(200);
        expect(response.body).toEqual({status: 'ok'});
    });
});
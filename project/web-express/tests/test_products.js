const request = require('supertest');
const app = require('../../src/app');

describe('Products', () => {
    it('should get a product by ID', async () => {
        const response = await request(app).get('/products/1');
        expect(response.status).toBe(200);
        expect(response.body.id).toBe(1);
    });

    it('should list all products', async () => {
        const response = await request(app).get('/products');
        expect(response.status).toBe(200);
        expect(response.body.length).toBeGreaterThan(0);
    });
});
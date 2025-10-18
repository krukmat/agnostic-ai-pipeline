import axios from 'axios';

const cart = {
  items: [],
  total: 0,
  addItem(item, quantity) {
    this.items.push({ item, quantity });
    this.total += item.price * quantity;
    return this;
  },
  removeItem(item, quantity) {
    const index = this.items.findIndex(i => i.item.id === item.id);
    if (index !== -1) {
      this.items.splice(index, 1);
      this.total -= item.price * quantity;
    }
    return this;
  },
  getItems() {
    return this.items;
  },
  getTotal() {
    return this.total;
  }
};

export default cart;

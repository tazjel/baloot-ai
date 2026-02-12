export class InventoryService {
    private static OWNED_KEY = 'baloot_owned_items';
    private static EQUIPPED_KEY = 'baloot_equipped_items';

    static getOwnedItems(): string[] {
        const saved = localStorage.getItem(this.OWNED_KEY);
        return saved ? JSON.parse(saved) : ['card_default', 'table_default'];
    }

    static saveOwnedItems(items: string[]): void {
        localStorage.setItem(this.OWNED_KEY, JSON.stringify(items));
    }

    static addOwnedItem(itemId: string): void {
        const items = this.getOwnedItems();
        if (!items.includes(itemId)) {
            items.push(itemId);
            this.saveOwnedItems(items);
        }
    }

    static getEquippedItems(): { card: string, table: string } {
        const saved = localStorage.getItem(this.EQUIPPED_KEY);
        return saved ? JSON.parse(saved) : { card: 'card_default', table: 'table_default' };
    }

    static saveEquippedItems(items: { card: string, table: string }): void {
        localStorage.setItem(this.EQUIPPED_KEY, JSON.stringify(items));
    }

    static equipItem(itemId: string, type: 'card' | 'table'): void {
        const current = this.getEquippedItems();
        const updated = { ...current, [type]: itemId };
        this.saveEquippedItems(updated);
    }
}

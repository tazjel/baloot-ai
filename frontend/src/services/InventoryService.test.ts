import { describe, it, expect, vi, beforeEach } from 'vitest';
import { InventoryService } from './InventoryService';

describe('InventoryService', () => {

    beforeEach(() => {
        localStorage.clear();
        vi.clearAllMocks();
    });

    it('getOwnedItems should return defaults if storage is empty', () => {
        const items = InventoryService.getOwnedItems();
        expect(items).toEqual(['card_default', 'table_default']);
    });

    it('getOwnedItems should return items from storage', () => {
        const saved = ['card_default', 'table_default', 'skin_1'];
        localStorage.setItem('baloot_owned_items', JSON.stringify(saved));

        const items = InventoryService.getOwnedItems();
        expect(items).toEqual(saved);
    });

    it('saveOwnedItems should save to storage', () => {
        const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
        const items = ['card_default', 'table_default', 'skin_2'];
        InventoryService.saveOwnedItems(items);

        expect(setItemSpy).toHaveBeenCalledWith('baloot_owned_items', JSON.stringify(items));
    });

    it('addOwnedItem should add item if not exists', () => {
        InventoryService.addOwnedItem('new_skin');
        const items = InventoryService.getOwnedItems();
        expect(items).toContain('new_skin');
        expect(items.length).toBe(3); // default 2 + 1
    });

    it('addOwnedItem should NOT add item if already exists', () => {
        InventoryService.addOwnedItem('card_default');
        const items = InventoryService.getOwnedItems();
        expect(items.length).toBe(2); // no dupes
    });

    it('getEquippedItems should return defaults if storage is empty', () => {
        const items = InventoryService.getEquippedItems();
        expect(items).toEqual({ card: 'card_default', table: 'table_default' });
    });

    it('equipItem should update equipped item', () => {
        const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
        InventoryService.equipItem('new_skin', 'card');
        const items = InventoryService.getEquippedItems();
        expect(items.card).toBe('new_skin');
        // Check persistence
        expect(setItemSpy).toHaveBeenCalledWith(
            'baloot_equipped_items',
            expect.stringContaining('"card":"new_skin"')
        );
    });
});

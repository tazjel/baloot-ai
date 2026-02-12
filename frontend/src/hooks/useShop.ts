import { useState, useEffect } from 'react';
import { UserProfile } from '../types';
import { AccountingEngine } from '../services/AccountingEngine';

export const useShop = (userProfile: UserProfile, handlePurchase: (itemId: string, cost: number) => void) => {
    const [isStoreOpen, setIsStoreOpen] = useState(false);

    // Item Persistence (UI)
    const [ownedItems, setOwnedItems] = useState<string[]>(() => AccountingEngine.Inventory.getOwnedItems());
    const [equippedItems, setEquippedItems] = useState<{ card: string, table: string }>(() => AccountingEngine.Inventory.getEquippedItems());

    useEffect(() => {
        AccountingEngine.Inventory.saveOwnedItems(ownedItems);
        AccountingEngine.Inventory.saveEquippedItems(equippedItems);
    }, [ownedItems, equippedItems]);

    const handlePurchaseWrapper = (itemId: string, cost: number) => {
        if (AccountingEngine.Purchase.canAfford(userProfile, cost)) {
            handlePurchase(itemId, cost);
            setOwnedItems(prev => [...prev, itemId]);
        }
    };

    const handleEquip = (itemId: string, type: 'card' | 'table') => setEquippedItems(prev => ({ ...prev, [type]: itemId }));

    return {
        isStoreOpen,
        setIsStoreOpen,
        ownedItems,
        equippedItems,
        handlePurchaseWrapper,
        handleEquip
    };
};

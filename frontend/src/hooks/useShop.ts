import { useState, useEffect, useRef } from 'react';
import { UserProfile } from '../types';
import { AccountingEngine } from '../services/AccountingEngine';
import { AuthService } from '../services/AuthService';

export const useShop = (userProfile: UserProfile, handlePurchase: (itemId: string, cost: number) => void) => {
    const [isStoreOpen, setIsStoreOpen] = useState(false);

    // Item Persistence (UI)
    const [ownedItems, setOwnedItems] = useState<string[]>(() =>
        (userProfile.ownedItems !== undefined && userProfile.ownedItems !== null)
            ? userProfile.ownedItems
            : AccountingEngine.Inventory.getOwnedItems()
    );
    const [equippedItems, setEquippedItems] = useState<{ card: string, table: string }>(() =>
        (userProfile.equippedItems !== undefined && userProfile.equippedItems !== null)
            ? userProfile.equippedItems
            : AccountingEngine.Inventory.getEquippedItems()
    );

    // Sync with UserProfile updates
    useEffect(() => {
        if (userProfile.ownedItems !== undefined && userProfile.ownedItems !== null) {
            setOwnedItems(userProfile.ownedItems);
        }
        if (userProfile.equippedItems !== undefined && userProfile.equippedItems !== null) {
            setEquippedItems(userProfile.equippedItems);
        }
    }, [userProfile.ownedItems, userProfile.equippedItems]);

    const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    // Keep refs for flush-on-unmount (closures in useEffect cleanup capture stale values)
    const ownedItemsRef = useRef(ownedItems);
    const equippedItemsRef = useRef(equippedItems);
    useEffect(() => { ownedItemsRef.current = ownedItems; }, [ownedItems]);
    useEffect(() => { equippedItemsRef.current = equippedItems; }, [equippedItems]);

    // Debounced localStorage persistence (500ms)
    useEffect(() => {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        saveTimerRef.current = setTimeout(() => {
            AccountingEngine.Inventory.saveOwnedItems(ownedItems);
            AccountingEngine.Inventory.saveEquippedItems(equippedItems);
            saveTimerRef.current = null;
        }, 500);
        return () => {
            if (saveTimerRef.current) {
                clearTimeout(saveTimerRef.current);
                // Flush pending save immediately on unmount to prevent data loss
                AccountingEngine.Inventory.saveOwnedItems(ownedItemsRef.current);
                AccountingEngine.Inventory.saveEquippedItems(equippedItemsRef.current);
            }
        };
    }, [ownedItems, equippedItems]);

    const handlePurchaseWrapper = async (itemId: string, cost: number) => {
        if (AuthService.getToken()) {
            try {
                const res = await AuthService.purchaseItem(itemId, cost);
                handlePurchase(itemId, cost);
                setOwnedItems(res.ownedItems);
            } catch (e) {
                console.error("Purchase failed", e);
            }
        } else {
            if (AccountingEngine.Purchase.canAfford(userProfile, cost)) {
                handlePurchase(itemId, cost);
                setOwnedItems(prev => [...prev, itemId]);
            }
        }
    };

    const handleEquip = async (itemId: string, type: 'card' | 'table') => {
        if (AuthService.getToken()) {
            try {
                await AuthService.equipItem(itemId, type);
            } catch (e) {
                console.error("Equip failed", e);
            }
        }
        setEquippedItems(prev => ({ ...prev, [type]: itemId }));
    };

    return {
        isStoreOpen,
        setIsStoreOpen,
        ownedItems,
        equippedItems,
        handlePurchaseWrapper,
        handleEquip
    };
};

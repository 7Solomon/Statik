import { useState } from 'react';
import type { Load, StructuralSystem } from '~/types/model';

type DisallowedType = 'DYNAMIC_LOADS' | 'NON_LINEAR_ELEMENTS' | 'CONSTRAINTS';

export const useSystemValidator = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<string[]>([]);

    const checkSystem = (system: StructuralSystem, notAllowed: DisallowedType[]): boolean => {
        const errors: string[] = [];

        // 1. CHECK DYNAMIC LOADS
        if (notAllowed.includes('DYNAMIC_LOADS')) {
            const hasDynamic = system.loads.some(l =>
                l.type === 'DYNAMIC_POINT' ||
                l.type === 'DYNAMIC_FORCE' ||
                l.type === 'DYNAMIC_MOMENT'
            );

            if (hasDynamic) {
                errors.push("Dynamic Loads (Time-History) are not allowed in Static Simplification.");
            }
        }

        // 2. CHECK CONSTRAINTS (Example)
        if (notAllowed.includes('CONSTRAINTS')) {
            if (system.constraints && system.constraints.length > 0) {
                errors.push("Constraints (Springs/Dampers) cannot be simplified statically.");
            }
        }

        if (errors.length > 0) {
            setMessages(errors);
            setIsOpen(true);
            return false; // Validation Failed
        }

        return true; // Validation Passed
    };

    const closeValidator = () => {
        setIsOpen(false);
        setMessages([]);
    };

    return {
        checkSystem,
        validatorProps: {
            isOpen,
            messages,
            onClose: closeValidator
        }
    };
};

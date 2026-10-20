import type { CSSProperties } from 'react';
/** Original Figma vector geometry, locally stored; currentColor changes only its state color. */
export function Icon({ name, size = 18, collection = 'overview' }: {
    name: string;
    size?: number;
    collection?: 'overview' | 'sidebar' | 'transactions' | 'categories' | 'wallets' | 'budgets' | 'goals' | 'insights' | 'assistant';
}) { return <span aria-hidden="true" className="overview-icon" style={{ width: size, height: size, maskImage: `url(/assets/${collection}/${name}.svg)`, WebkitMaskImage: `url(/assets/${collection}/${name}.svg)` } as CSSProperties}/>; }

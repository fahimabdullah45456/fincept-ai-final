export type Period = 'this_month' | 'this_week' | 'last_month' | 'this_year' | 'custom';
export type Grouping = 'weekly' | 'monthly' | 'yearly';
export type Query = {
    period: Period;
    dataset: 'live' | 'demo';
    start?: string;
    end?: string;
};
export type Totals = {
    income: number;
    expenses: number;
    net: number;
    savings_rate: number | null;
};
export type Budget = {
    id: string;
    name: string;
    category: string;
    spent: number;
    limit: number;
    remaining: number;
    percentage: number | null;
    status: string;
};
export type Goal = {
    id: string;
    name: string;
    saved: number;
    target: number;
    remaining: number;
    target_date: string | null;
    percentage: number | null;
};
export type Bucket = Totals & {
    label: string;
    full_label: string;
    start: string;
    end: string;
    selected: boolean;
};
export type OverviewData = {
    dataset: string;
    reporting_period: {
        start: string;
        end: string;
        previous_start: string;
        previous_end: string;
        label: string;
        days_left: number;
    };
    summary: Totals & {
        available_balance: number;
        wallet_count: number;
        balance_change: number;
        previous: Totals;
        income_change: number | null;
        expense_change: number | null;
        savings_change: number | null;
    };
    categories: {
        name: string;
        amount: number;
        percentage: number;
    }[];
    cash_flow: {
        grouping: Grouping;
        history_start: string;
        history_end: string;
        buckets: Bucket[];
    };
    budgets: Budget[];
    goals: Goal[];
};
export type Insight = {
    kind: 'budget_over' | 'budget_near';
    budget: Budget;
} | {
    kind: 'negative_cash_flow';
    net: number;
};
export type Transaction = {
    id: string;
    title: string;
    description: string;
    category: string;
    kind: 'income' | 'expense' | 'transfer';
    amount: number;
    date: string;
};
export type Recent = {
    items: Transaction[];
    total: number;
    page: number;
    limit: number;
};

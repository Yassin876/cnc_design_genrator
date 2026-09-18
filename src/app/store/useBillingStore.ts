import { create } from 'zustand';
import { billingApiService } from '../../services/api/billing';
import { PlanId, PlanDetails, SubscriptionStatus, PaymentConfig, PaymentRecord } from '../../types';

interface BillingState {
  status: SubscriptionStatus | null;
  plan: PlanId;
  planDisplayName: string;
  requestsUsed: number;
  requestsLimit: number;
  requestsRemaining: number;
  cycleStartDate: string | null;
  cycleEndDate: string | null;
  isAdmin: boolean;
  plansCatalog: Record<string, PlanDetails>;
  paymentConfig: PaymentConfig | null;
  paymentHistory: PaymentRecord[];
  adminPayments: PaymentRecord[];
  isLoading: boolean;
  isSubmittingPayment: boolean;
  error: string | null;

  fetchBillingStatus: (userId?: string) => Promise<SubscriptionStatus | null>;
  fetchPaymentConfig: () => Promise<PaymentConfig | null>;
  fetchPaymentHistory: () => Promise<void>;
  fetchAdminPayments: (statusFilter?: string) => Promise<void>;
  submitPaymentRequest: (planRequested: string, method: string, proofReference?: string) => Promise<any>;
  uploadPaymentProof: (file: File, planRequested: string, method: string, proofReference?: string) => Promise<any>;
  approvePayment: (paymentId: string, notes?: string) => Promise<any>;
  rejectPayment: (paymentId: string, reason?: string) => Promise<any>;
  mockCheckout: (planRequested: string) => Promise<any>;
}

export const useBillingStore = create<BillingState>((set, get) => ({
  status: null,
  plan: 'free',
  planDisplayName: 'Free',
  requestsUsed: 0,
  requestsLimit: 15,
  requestsRemaining: 15,
  cycleStartDate: null,
  cycleEndDate: null,
  isAdmin: false,
  plansCatalog: {},
  paymentConfig: null,
  paymentHistory: [],
  adminPayments: [],
  isLoading: false,
  isSubmittingPayment: false,
  error: null,

  fetchBillingStatus: async (userId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await billingApiService.getBillingStatus(userId);
      set({
        status: data,
        plan: data.plan,
        planDisplayName: data.plan_display_name,
        requestsUsed: data.requests_used,
        requestsLimit: data.requests_limit,
        requestsRemaining: data.requests_remaining,
        cycleStartDate: data.cycle_start_date,
        cycleEndDate: data.cycle_end_date,
        isAdmin: data.is_admin,
        plansCatalog: data.plans_catalog || {},
        isLoading: false
      });
      return data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to load billing status';
      set({ error: msg, isLoading: false });
      return null;
    }
  },

  fetchPaymentConfig: async () => {
    try {
      const config = await billingApiService.getPaymentConfig();
      set({ paymentConfig: config });
      return config;
    } catch (err: any) {
      console.error('Failed to load payment config', err);
      return null;
    }
  },

  fetchPaymentHistory: async () => {
    try {
      const data = await billingApiService.getPaymentHistory();
      set({ paymentHistory: data.payments || [] });
    } catch (err: any) {
      console.error('Failed to fetch user payment history', err);
    }
  },

  fetchAdminPayments: async (statusFilter?: string) => {
    set({ isLoading: true });
    try {
      const data = await billingApiService.listAdminPayments(statusFilter);
      set({ adminPayments: data.payments || [], isLoading: false });
    } catch (err: any) {
      set({ isLoading: false, error: err.response?.data?.detail || 'Failed to fetch admin payments' });
    }
  },

  submitPaymentRequest: async (planRequested: string, method: string, proofReference?: string) => {
    set({ isSubmittingPayment: true, error: null });
    try {
      const res = await billingApiService.submitPaymentRequest(planRequested, method, proofReference);
      await get().fetchPaymentHistory();
      set({ isSubmittingPayment: false });
      return res;
    } catch (err: any) {
      set({ isSubmittingPayment: false });
      throw err;
    }
  },

  uploadPaymentProof: async (file: File, planRequested: string, method: string, proofReference?: string) => {
    set({ isSubmittingPayment: true, error: null });
    try {
      const res = await billingApiService.uploadPaymentProof(file, planRequested, method, proofReference);
      await get().fetchPaymentHistory();
      set({ isSubmittingPayment: false });
      return res;
    } catch (err: any) {
      set({ isSubmittingPayment: false });
      throw err;
    }
  },

  approvePayment: async (paymentId: string, notes?: string) => {
    try {
      const res = await billingApiService.approvePayment(paymentId, notes);
      await get().fetchAdminPayments();
      await get().fetchBillingStatus();
      return res;
    } catch (err: any) {
      throw err;
    }
  },

  rejectPayment: async (paymentId: string, reason?: string) => {
    try {
      const res = await billingApiService.rejectPayment(paymentId, reason);
      await get().fetchAdminPayments();
      return res;
    } catch (err: any) {
      throw err;
    }
  },

  mockCheckout: async (planRequested: string) => {
    set({ isSubmittingPayment: true, error: null });
    try {
      const res = await billingApiService.mockCheckout(planRequested);
      await get().fetchBillingStatus();
      await get().fetchPaymentHistory();
      set({ isSubmittingPayment: false });
      return res;
    } catch (err: any) {
      set({ isSubmittingPayment: false });
      throw err;
    }
  },
}));

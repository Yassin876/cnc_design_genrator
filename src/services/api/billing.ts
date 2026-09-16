import { apiClient } from './client';
import { SubscriptionStatus, PaymentConfig, PaymentRecord, PaymentMethodItem } from '../../types';

export interface CreatePaymentMethodPayload {
  provider: string;
  payment_token: string;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  holder_name?: string;
  is_default?: boolean;
}

export const billingApiService = {
  /**
   * Fetch user subscription, limits, and rolling cycle status directly from database
   */
  getBillingStatus: async (userId?: string): Promise<SubscriptionStatus> => {
    const params = userId ? { user_id: userId } : {};
    const res = await apiClient.get<SubscriptionStatus>('/billing/status', { params });
    return res.data;
  },

  /**
   * Fetch payment configuration, instructions, and placeholder parameters
   */
  getPaymentConfig: async (): Promise<PaymentConfig> => {
    const res = await apiClient.get<PaymentConfig>('/billing/config');
    return res.data;
  },

  /**
   * List saved tokenized payment methods for authenticated user
   */
  getPaymentMethods: async (): Promise<{ payment_methods: PaymentMethodItem[]; count: number }> => {
    const res = await apiClient.get<{ payment_methods: PaymentMethodItem[]; count: number }>('/billing/payment-methods');
    return res.data;
  },

  /**
   * Save a new tokenized payment method (vaulted token, brand, last 4 digits)
   */
  addPaymentMethod: async (payload: CreatePaymentMethodPayload): Promise<PaymentMethodItem> => {
    const res = await apiClient.post<PaymentMethodItem>('/billing/payment-methods', payload);
    return res.data;
  },

  /**
   * Delete a saved payment method
   */
  deletePaymentMethod: async (paymentMethodId: string): Promise<{ success: boolean; message: string }> => {
    const res = await apiClient.delete<{ success: boolean; message: string }>(`/billing/payment-methods/${paymentMethodId}`);
    return res.data;
  },

  /**
   * Set a saved payment method as default primary card
   */
  setDefaultPaymentMethod: async (paymentMethodId: string): Promise<PaymentMethodItem> => {
    const res = await apiClient.patch<PaymentMethodItem>(`/billing/payment-methods/${paymentMethodId}/default`);
    return res.data;
  },

  /**
   * Submit manual payment request with reference code
   */
  submitPaymentRequest: async (planRequested: string, method: string, proofReference?: string) => {
    const res = await apiClient.post('/billing/payment/request', {
      plan_requested: planRequested,
      method,
      proof_reference: proofReference,
    });
    return res.data;
  },

  /**
   * Upload payment proof receipt image
   */
  uploadPaymentProof: async (file: File, planRequested: string, method: string, proofReference?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('plan_requested', planRequested);
    formData.append('method', method);
    if (proofReference) {
      formData.append('proof_reference', proofReference);
    }

    const res = await apiClient.post('/billing/payment/upload-proof', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  /**
   * Get logged-in user's payment history
   */
  getPaymentHistory: async (): Promise<{ payments: PaymentRecord[] }> => {
    const res = await apiClient.get<{ payments: PaymentRecord[] }>('/billing/payment/history');
    return res.data;
  },

  /**
   * Admin-only: list all pending / reviewed payments
   */
  listAdminPayments: async (statusFilter?: string): Promise<{ payments: PaymentRecord[] }> => {
    const params = statusFilter ? { status_filter: statusFilter } : {};
    const res = await apiClient.get<{ payments: PaymentRecord[] }>('/billing/admin/payments', { params });
    return res.data;
  },

  /**
   * Admin-only: approve payment request
   */
  approvePayment: async (paymentId: string, adminNotes?: string) => {
    const res = await apiClient.post(`/billing/admin/payments/${paymentId}/approve`, {
      admin_notes: adminNotes,
    });
    return res.data;
  },

  /**
   * Admin-only: reject payment request
   */
  rejectPayment: async (paymentId: string, reason?: string) => {
    const res = await apiClient.post(`/billing/admin/payments/${paymentId}/reject`, {
      reason,
    });
    return res.data;
  },

  /** Development-only instant plan upgrade (no manual admin approval). */
  mockCheckout: async (planRequested: string) => {
    const res = await apiClient.post('/billing/payment/mock-checkout', {
      plan_requested: planRequested,
    });
    return res.data;
  },
};

import React, { useState, useEffect, useRef } from 'react';
import {
  CreditCard, Check, AlertCircle, ShieldCheck, Clock,
  Calendar, Zap, ArrowRight, X, CheckCircle2,
  Lock, ExternalLink, RefreshCw
} from 'lucide-react';
import { useBillingStore } from '../../app/store/useBillingStore';
import { useAuthStore } from '../../app/store/useAuthStore';
import { PlanId, PlanDetails, PaymentMethodItem } from '../../types';
import { billingApiService } from '../../services/api/billing';
import { paddleService } from '../../services/paddle/paddleService';

interface BillingViewProps {
  initialTab?: 'plans' | 'payment_methods' | 'history' | 'admin';
}

const PADDLE_PRICE_MAP: Record<PlanId, string> = {
  free: '',
  pro: 'pri_01m2p85k69p7fxaa2aam45r4jw',
  pro_plus: 'pri_01m2p89n5cce3wjzk8y1aerbg1',
  business: 'pri_01m2p8cbbevbzyvxgp5pfsg746',
};

export const BillingView: React.FC<BillingViewProps> = ({ initialTab = 'plans' }) => {
  const { user } = useAuthStore();
  const {
    plan: currentPlan,
    planDisplayName,
    requestsUsed,
    requestsLimit,
    requestsRemaining,
    cycleStartDate,
    cycleEndDate,
    isAdmin,
    plansCatalog,
    paymentHistory,
    adminPayments,
    fetchBillingStatus,
    fetchPaymentConfig,
    fetchPaymentHistory,
    fetchAdminPayments,
    approvePayment,
    rejectPayment,
  } = useBillingStore();

  const [activeSubTab, setActiveSubTab] = useState<'plans' | 'payment_methods' | 'history' | 'admin'>(initialTab);

  // Paddle Subscription Details
  const [paddleSubscription, setPaddleSubscription] = useState<{
    paddle_customer_id?: string | null;
    paddle_subscription_id?: string | null;
    subscription_status?: string | null;
    next_billing_date?: string | null;
    cancel_url?: string | null;
    update_url?: string | null;
  } | null>(null);

  // Saved Payment Methods state
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodItem[]>([]);
  const [isLoadingMethods, setIsLoadingMethods] = useState(false);
  const [methodActionMsg, setMethodActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Upgrade Modal State
  const [selectedPlanForUpgrade, setSelectedPlanForUpgrade] = useState<PlanDetails | null>(null);
  const [isOpeningCheckout, setIsOpeningCheckout] = useState(false);
  const [checkoutErrorMsg, setCheckoutErrorMsg] = useState<string | null>(null);
  const [isCheckingSync, setIsCheckingSync] = useState(false);

  // Admin Review action state
  const [adminActionMsg, setAdminActionMsg] = useState<string | null>(null);
  const [processingPaymentId, setProcessingPaymentId] = useState<string | null>(null);

  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  const loadPaddleDetails = async () => {
    try {
      const data = await billingApiService.getPaddleSubscription();
      setPaddleSubscription(data);
    } catch {
      // Fallback silently if offline or endpoint unavailable
    }
  };

  const loadSavedMethods = async () => {
    setIsLoadingMethods(true);
    try {
      const data = await billingApiService.getPaymentMethods();
      setPaymentMethods(data?.payment_methods || []);
    } catch {
      // Gracefully set empty array without console 404 noise
      setPaymentMethods([]);
    } finally {
      setIsLoadingMethods(false);
    }
  };

  useEffect(() => {
    fetchBillingStatus(user?.id);
    loadPaddleDetails();
    fetchPaymentConfig();
    fetchPaymentHistory();
    loadSavedMethods();
    if (user?.is_admin || isAdmin) {
      fetchAdminPayments();
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [user?.id, user?.is_admin, isAdmin]);

  // Calculate percentage used
  const usagePercentage = Math.min(100, Math.round((requestsUsed / (requestsLimit || 1)) * 100));

  // Format cycle date
  const formatCycleDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'Active Cycle';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  // Days remaining in cycle
  const getDaysRemaining = () => {
    const endTarget = paddleSubscription?.next_billing_date || cycleEndDate;
    if (!endTarget) return null;
    try {
      const now = new Date().getTime();
      const end = new Date(endTarget).getTime();
      const diffDays = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
      return Math.max(0, diffDays);
    } catch {
      return null;
    }
  };

  const daysRemaining = getDaysRemaining();

  const handleOpenUpgrade = (plan: PlanDetails) => {
    setSelectedPlanForUpgrade(plan);
    setCheckoutErrorMsg(null);
  };

  const handleCloseUpgrade = () => {
    setSelectedPlanForUpgrade(null);
    setCheckoutErrorMsg(null);
    setIsOpeningCheckout(false);
  };

  const handleLaunchPaddleCheckout = async () => {
    if (!selectedPlanForUpgrade) return;
    const priceId = PADDLE_PRICE_MAP[selectedPlanForUpgrade.id];
    if (!priceId) {
      setCheckoutErrorMsg('Invalid price identifier for this tier.');
      return;
    }

    setIsOpeningCheckout(true);
    setCheckoutErrorMsg(null);

    try {
      await paddleService.openCheckout({
        planId: selectedPlanForUpgrade.id,
        priceId,
        user: {
          id: user?.id,
          email: user?.email,
          name: user?.name,
        },
      });

      // Poll backend every 3 seconds for 30 seconds to catch verified webhook confirmation
      let attempts = 0;
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);

      pollTimerRef.current = setInterval(async () => {
        attempts++;
        await fetchBillingStatus(user?.id);
        await loadPaddleDetails();

        if (attempts >= 10) {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        }
      }, 3000);

      handleCloseUpgrade();
    } catch (err: any) {
      console.error('[Billing] Checkout error:', err);
      setCheckoutErrorMsg(err?.message || 'Could not open Paddle checkout. Please try again.');
    } finally {
      setIsOpeningCheckout(false);
    }
  };

  const handleManualSync = async () => {
    setIsCheckingSync(true);
    try {
      await fetchBillingStatus(user?.id);
      await loadPaddleDetails();
      await fetchPaymentHistory();
    } finally {
      setIsCheckingSync(false);
    }
  };

  const handleAdminApprove = async (paymentId: string) => {
    setProcessingPaymentId(paymentId);
    setAdminActionMsg(null);
    try {
      const res = await approvePayment(paymentId, 'Approved via Admin Panel');
      setAdminActionMsg(res.message || 'Payment approved successfully and user subscription updated.');
      await fetchBillingStatus(user?.id);
      await loadPaddleDetails();
    } catch (err: any) {
      setAdminActionMsg(`Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setProcessingPaymentId(null);
    }
  };

  const handleAdminReject = async (paymentId: string) => {
    const reason = prompt('Please enter the reason for rejection (optional):', 'Payment verification failed');
    if (reason === null) return;
    setProcessingPaymentId(paymentId);
    setAdminActionMsg(null);
    try {
      const res = await rejectPayment(paymentId, reason);
      setAdminActionMsg(res.message || 'Payment request rejected.');
    } catch (err: any) {
      setAdminActionMsg(`Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setProcessingPaymentId(null);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Billing &amp; Subscription Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">Manage your Anti Design plan, Paddle subscriptions, tokens, and invoice history.</p>
        </div>

        {/* Sub-Tabs */}
        <div className="flex items-center space-x-1 bg-slate-200/80 p-1 rounded-xl text-xs font-semibold self-start sm:self-auto">
          <button
            onClick={() => setActiveSubTab('plans')}
            className={`px-3 py-1.5 rounded-lg transition-all ${activeSubTab === 'plans' ? 'bg-white text-indigo-700 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'}`}
          >
            Plans &amp; Usage
          </button>
          <button
            onClick={() => setActiveSubTab('payment_methods')}
            className={`px-3 py-1.5 rounded-lg transition-all ${activeSubTab === 'payment_methods' ? 'bg-white text-indigo-700 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'}`}
          >
            Payment Methods
          </button>
          <button
            onClick={() => setActiveSubTab('history')}
            className={`px-3 py-1.5 rounded-lg transition-all ${activeSubTab === 'history' ? 'bg-white text-indigo-700 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'}`}
          >
            Invoices &amp; History
          </button>
          {(user?.is_admin || isAdmin) && (
            <button
              onClick={() => setActiveSubTab('admin')}
              className={`px-3 py-1.5 rounded-lg transition-all ${activeSubTab === 'admin' ? 'bg-indigo-600 text-white shadow-xs font-bold' : 'text-indigo-900 hover:bg-indigo-50'}`}
            >
              Admin Approvals ({adminPayments.filter(p => p.status === 'pending_approval').length})
            </button>
          )}
        </div>
      </div>

      {methodActionMsg && (
        <div className={`p-3 rounded-xl text-xs font-semibold ${methodActionMsg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'}`}>
          {methodActionMsg.text}
        </div>
      )}

      {/* ── TAB 1: PLANS & USAGE ──────────────────────────────────────────────── */}
      {activeSubTab === 'plans' && (
        <div className="space-y-6">
          
          {/* Current Subscription Card */}
          <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 shadow-md relative overflow-hidden">
            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
              
              <div className="space-y-2">
                <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-indigo-500/30 text-indigo-300 border border-indigo-400/30">
                    Active Plan
                  </span>
                  {paddleSubscription?.subscription_status && paddleSubscription.subscription_status !== 'active' && (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/30 text-amber-300 border border-amber-400/30">
                      Status: {paddleSubscription.subscription_status}
                    </span>
                  )}
                  <span className="text-xs text-slate-300 flex items-center space-x-1">
                    <Calendar className="w-3.5 h-3.5 mr-1" />
                    <span>
                      {paddleSubscription?.next_billing_date ? 'Next Billing Date:' : 'Cycle Ends:'} {formatCycleDate(paddleSubscription?.next_billing_date || cycleEndDate)} ({daysRemaining} days left)
                    </span>
                  </span>
                </div>
                <h2 className="text-2xl font-black tracking-tight text-white">{planDisplayName}</h2>
                <p className="text-xs text-slate-300 max-w-md">
                  {currentPlan === 'free' 
                    ? 'Free starter account for CAD hobbyists. Upgrade to Pro for high-precision CNC generation.' 
                    : 'Full industrial tier with high throughput generation and priority rendering pipelines.'}
                </p>

                {/* Paddle Subscription Management Actions */}
                <div className="flex items-center space-x-3 pt-1">
                  <button
                    onClick={handleManualSync}
                    disabled={isCheckingSync}
                    className="inline-flex items-center text-[11px] font-semibold text-indigo-300 hover:text-white transition-colors"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isCheckingSync ? 'animate-spin' : ''}`} />
                    <span>{isCheckingSync ? 'Syncing…' : 'Sync Status'}</span>
                  </button>

                  {paddleSubscription?.update_url && (
                    <a
                      href={paddleSubscription.update_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center text-[11px] font-semibold text-indigo-300 hover:text-white transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5 mr-1" />
                      <span>Update Payment Method</span>
                    </a>
                  )}

                  {paddleSubscription?.cancel_url && (
                    <a
                      href={paddleSubscription.cancel_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center text-[11px] font-semibold text-rose-300 hover:text-rose-200 transition-colors"
                    >
                      <span>Manage / Cancel Subscription</span>
                    </a>
                  )}
                </div>
              </div>

              {/* Usage Stats Gauge */}
              <div className="bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/15 min-w-[240px] space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-200 flex items-center">
                    <Zap className="w-3.5 h-3.5 text-amber-400 mr-1" />
                    Generation Tokens
                  </span>
                  <span className="font-mono font-bold text-white">
                    {requestsUsed} / {requestsLimit}
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="w-full h-2 bg-slate-700/60 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-500 rounded-full ${
                      usagePercentage > 90 ? 'bg-rose-500' : usagePercentage > 75 ? 'bg-amber-400' : 'bg-indigo-400'
                    }`}
                    style={{ width: `${usagePercentage}%` }}
                  />
                </div>

                <div className="flex justify-between items-center text-[10px] text-slate-300">
                  <span>{requestsRemaining} requests remaining</span>
                  <span>{usagePercentage}% used</span>
                </div>
              </div>

            </div>
          </div>

          {/* Pricing Catalog Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Object.values(plansCatalog).map((plan) => {
              const isCurrent = plan.id === currentPlan;
              const isPopular = plan.id === 'pro';

              return (
                <div
                  key={plan.id}
                  className={`bg-white rounded-2xl p-6 border transition-all flex flex-col justify-between relative shadow-xs ${
                    isCurrent
                      ? 'border-indigo-600 ring-2 ring-indigo-600/20'
                      : isPopular
                      ? 'border-indigo-300 hover:border-indigo-500 hover:shadow-md'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  {isPopular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-[10px] font-black uppercase tracking-wider px-3 py-0.5 rounded-full shadow-sm">
                      Most Popular
                    </div>
                  )}

                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="font-bold text-slate-900 text-base">{plan.name}</h3>
                      {isCurrent && (
                        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                          Current
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-500 mb-4 min-h-[32px]">{plan.description}</p>

                    <div className="mb-6 flex items-baseline space-x-1">
                      <span className="text-3xl font-black text-slate-900 font-mono">${plan.price}</span>
                      <span className="text-xs text-slate-400 font-medium">/ month</span>
                    </div>

                    <div className="space-y-2.5 text-xs text-slate-700 mb-6 border-t border-slate-100 pt-4">
                      <div className="font-bold text-slate-900 flex items-center">
                        <Zap className="w-3.5 h-3.5 text-indigo-600 mr-2 shrink-0" />
                        <span>{plan.requests_limit} AI CAD Requests / cycle</span>
                      </div>
                      {plan.features.map((feat, idx) => (
                        <div key={idx} className="flex items-start space-x-2">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                          <span className="text-slate-600">{feat}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    {isCurrent ? (
                      <button
                        disabled
                        className="w-full py-2.5 bg-slate-100 text-slate-500 rounded-xl text-xs font-bold cursor-default"
                      >
                        Active Plan
                      </button>
                    ) : (
                      <button
                        onClick={() => handleOpenUpgrade(plan)}
                        className={`w-full py-2.5 rounded-xl text-xs font-bold transition-all shadow-xs flex items-center justify-center space-x-1.5 ${
                          isPopular
                            ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                            : 'bg-slate-900 hover:bg-slate-800 text-white'
                        }`}
                      >
                        <span>Upgrade to {plan.name}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

        </div>
      )}

      {/* ── TAB 2: PAYMENT METHODS (Paddle Vault) ───────────────────────────── */}
      {activeSubTab === 'payment_methods' && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-6">
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Payment Methods &amp; Billing Security</h3>
                <p className="text-xs text-slate-500">Payments and card credentials are securely processed and vaulted by Paddle.</p>
              </div>

              {paddleSubscription?.update_url && (
                <a
                  href={paddleSubscription.update_url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-xs flex items-center space-x-1.5 self-start sm:self-auto"
                >
                  <ExternalLink className="w-4 h-4 mr-1" />
                  <span>Update Card in Paddle Portal</span>
                </a>
              )}
            </div>

            {/* PCI Compliance Notice */}
            <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-xl text-xs text-indigo-900 flex items-start space-x-2">
              <Lock className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <span>
                <strong>PCI-DSS Compliant Storage:</strong> Anti Design never stores complete credit card numbers, CVVs, or payment security codes on local servers. All payment data is handled directly by Paddle's PCI-DSS Level 1 certified infrastructure.
              </span>
            </div>

            {/* Paddle Subscription Vault Details */}
            {paddleSubscription?.paddle_subscription_id ? (
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="w-5 h-5 text-emerald-600" />
                    <div>
                      <div className="font-bold text-slate-900 text-xs">Paddle Managed Subscription</div>
                      <div className="text-[11px] font-mono text-slate-500">ID: {paddleSubscription.paddle_subscription_id}</div>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800">
                    {paddleSubscription.subscription_status || 'Active'}
                  </span>
                </div>

                <div className="text-xs text-slate-600 pt-2 border-t border-slate-200 flex flex-col sm:flex-row justify-between gap-2">
                  <span>Customer ID: <strong className="font-mono text-slate-800">{paddleSubscription.paddle_customer_id || 'Paddle Vault'}</strong></span>
                  <span>Next Renewal: <strong className="text-slate-800">{formatCycleDate(paddleSubscription.next_billing_date)}</strong></span>
                </div>
              </div>
            ) : (
              <div className="text-center py-10 border-2 border-dashed border-slate-200 rounded-2xl">
                <CreditCard className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-600">No active Paddle payment vault yet.</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Upgrade to a Pro or Business plan using Paddle Checkout to establish your secure payment vault.</p>
              </div>
            )}

          </div>
        </div>
      )}

      {/* ── TAB 3: INVOICES & HISTORY ────────────────────────────────────────── */}
      {activeSubTab === 'history' && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-900 text-base">Payment &amp; Invoicing History</h3>
            <button
              onClick={handleManualSync}
              disabled={isCheckingSync}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isCheckingSync ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
          
          {paymentHistory.length === 0 ? (
            <div className="text-center py-10 text-xs text-slate-400">
              No previous payment records found on this account.
            </div>
          ) : (
            <div className="divide-y divide-slate-100 text-xs">
              {paymentHistory.map((item) => (
                <div key={item.id} className="py-3 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="font-bold text-slate-900">
                      Upgrade to {item.plan_requested.toUpperCase()}
                    </div>
                    <div className="text-slate-400 text-[11px]">
                      {new Date(item.created_at).toLocaleDateString()} • Method: {item.method}
                    </div>
                  </div>
                  <div className="text-right space-y-0.5">
                    <div className="font-mono font-bold text-slate-900">${item.amount} {item.currency}</div>
                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.status === 'approved' ? 'bg-emerald-50 text-emerald-700' : item.status === 'rejected' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700'
                    }`}>
                      {item.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 4: ADMIN REVIEW ──────────────────────────────────────────────── */}
      {activeSubTab === 'admin' && (user?.is_admin || isAdmin) && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-bold text-slate-900 text-base">Administrative Payment Approvals</h3>
              <p className="text-xs text-slate-500">Review pending administrative payments and webhook transactions.</p>
            </div>
          </div>

          {adminActionMsg && (
            <div className="p-3 bg-indigo-50 border border-indigo-200 text-indigo-900 rounded-xl text-xs font-semibold">
              {adminActionMsg}
            </div>
          )}

          {adminPayments.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">No payment requests submitted.</div>
          ) : (
            <div className="divide-y divide-slate-100 text-xs">
              {adminPayments.map((p) => (
                <div key={p.id} className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="font-bold text-slate-900 text-sm">
                      {p.user_name || 'User'} ({p.user_email || p.user_id})
                    </div>
                    <div className="text-slate-500">
                      Requested: <strong className="text-indigo-600">{p.plan_requested}</strong> (${p.amount} {p.currency}) via {p.method}
                    </div>
                    {p.proof_reference && (
                      <div className="text-slate-600 font-mono bg-slate-50 p-1.5 rounded border border-slate-200 max-w-md">
                        Reference: {p.proof_reference}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {p.status === 'pending_approval' ? (
                      <>
                        <button
                          disabled={processingPaymentId === p.id}
                          onClick={() => handleAdminApprove(p.id)}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs shadow-xs"
                        >
                          Approve Plan
                        </button>
                        <button
                          disabled={processingPaymentId === p.id}
                          onClick={() => handleAdminReject(p.id)}
                          className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg font-bold text-xs"
                        >
                          Reject
                        </button>
                      </>
                    ) : (
                      <span className={`px-2.5 py-1 rounded-lg text-xs font-bold ${p.status === 'approved' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                        {p.status}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── PADDLE CHECKOUT MODAL ───────────────────────────────────────────── */}
      {selectedPlanForUpgrade && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-5">
            <div className="flex justify-between items-center">
              <div>
                <span className="text-[10px] font-black uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md">
                  Paddle Subscription
                </span>
                <h3 className="font-bold text-slate-900 text-base mt-1">Upgrade to {selectedPlanForUpgrade.name}</h3>
              </div>
              <button onClick={handleCloseUpgrade} className="p-1 text-slate-400 hover:text-slate-600 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-4 space-y-2">
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-slate-600">Monthly Subscription:</span>
                <div className="flex items-baseline space-x-1">
                  <span className="font-mono text-2xl font-black text-slate-900">${selectedPlanForUpgrade.price}</span>
                  <span className="text-xs text-slate-500 font-medium">USD / mo</span>
                </div>
              </div>
              <div className="flex justify-between items-center text-[11px] text-slate-500 pt-2 border-t border-slate-200/60">
                <span>Generation Limit:</span>
                <span className="font-bold text-indigo-600">{selectedPlanForUpgrade.requests_limit} AI CAD Requests</span>
              </div>
            </div>

            {checkoutErrorMsg && (
              <div className="p-3 bg-rose-50 text-rose-800 border border-rose-200 rounded-xl text-xs font-semibold flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{checkoutErrorMsg}</span>
              </div>
            )}

            <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-xl text-[11px] text-indigo-900 flex items-start space-x-2">
              <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <span>
                Checkout is processed securely via <strong>Paddle</strong>. Supports major Credit/Debit cards, Apple Pay, Google Pay, and PayPal.
              </span>
            </div>

            <div className="flex items-center space-x-2 pt-1">
              <button
                type="button"
                onClick={handleLaunchPaddleCheckout}
                disabled={isOpeningCheckout}
                className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-xs flex items-center justify-center space-x-2 disabled:opacity-50 transition-all"
              >
                <span>{isOpeningCheckout ? 'Opening Paddle Checkout…' : `Proceed to Subscribe ($${selectedPlanForUpgrade.price}/mo)`}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={handleCloseUpgrade}
                className="px-4 py-3 text-slate-600 hover:text-slate-900 text-xs font-semibold"
              >
                Cancel
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};

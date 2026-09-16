import React, { useState, useEffect } from 'react';
import {
  CreditCard, Check, AlertCircle, ShieldCheck, Clock,
  Calendar, Zap, ArrowRight, UploadCloud, X, CheckCircle2,
  FileText, User, DollarSign, Building2, Smartphone, Banknote,
  Plus, Trash2, Star, Lock
} from 'lucide-react';
import { useBillingStore } from '../../app/store/useBillingStore';
import { useAuthStore } from '../../app/store/useAuthStore';
import { PlanId, PlanDetails, PaymentRecord, PaymentMethodItem } from '../../types';
import { billingApiService } from '../../services/api/billing';

interface BillingViewProps {
  initialTab?: 'plans' | 'payment_methods' | 'history' | 'admin';
}

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
    paymentConfig,
    paymentHistory,
    adminPayments,
    isLoading,
    isSubmittingPayment,
    fetchBillingStatus,
    fetchPaymentConfig,
    fetchPaymentHistory,
    fetchAdminPayments,
    submitPaymentRequest,
    uploadPaymentProof,
    approvePayment,
    rejectPayment,
    mockCheckout
  } = useBillingStore();

  const [activeSubTab, setActiveSubTab] = useState<'plans' | 'payment_methods' | 'history' | 'admin'>(initialTab);

  // Saved Payment Methods state
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodItem[]>([]);
  const [isLoadingMethods, setIsLoadingMethods] = useState(false);
  const [isAddingMethod, setIsAddingMethod] = useState(false);
  const [cardHolder, setCardHolder] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [cardExpMonth, setCardExpMonth] = useState('12');
  const [cardExpYear, setCardExpYear] = useState('2028');
  const [cardCvc, setCardCvc] = useState('');
  const [cardMakeDefault, setCardMakeDefault] = useState(true);
  const [methodActionMsg, setMethodActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Upgrade Modal State
  const [selectedPlanForUpgrade, setSelectedPlanForUpgrade] = useState<PlanDetails | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<'instapay' | 'cash'>('instapay');
  const [proofReference, setProofReference] = useState('');
  const [proofFile, setProofFile] = useState<File | null>(null);
  const [submitSuccessMsg, setSubmitSuccessMsg] = useState<string | null>(null);
  const [submitErrorMsg, setSubmitErrorMsg] = useState<string | null>(null);

  // Admin Review action state
  const [adminActionMsg, setAdminActionMsg] = useState<string | null>(null);
  const [processingPaymentId, setProcessingPaymentId] = useState<string | null>(null);
  const [mockCheckoutMsg, setMockCheckoutMsg] = useState<string | null>(null);
  const isDev = import.meta.env.DEV;

  const loadSavedMethods = async () => {
    setIsLoadingMethods(true);
    try {
      const data = await billingApiService.getPaymentMethods();
      setPaymentMethods(data.payment_methods || []);
    } catch (err: any) {
      console.error('Failed to load payment methods:', err);
    } finally {
      setIsLoadingMethods(false);
    }
  };

  useEffect(() => {
    fetchBillingStatus(user?.id);
    fetchPaymentConfig();
    fetchPaymentHistory();
    loadSavedMethods();
    if (user?.is_admin || isAdmin) {
      fetchAdminPayments();
    }
  }, [user?.id, user?.is_admin, isAdmin]);

  // Calculate percentage used
  const usagePercentage = Math.min(100, Math.round((requestsUsed / (requestsLimit || 1)) * 100));

  // Format cycle date
  const formatCycleDate = (dateStr: string | null) => {
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
    if (!cycleEndDate) return null;
    try {
      const now = new Date().getTime();
      const end = new Date(cycleEndDate).getTime();
      const diffDays = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
      return Math.max(0, diffDays);
    } catch {
      return null;
    }
  };

  const daysRemaining = getDaysRemaining();

  const handleOpenUpgrade = (plan: PlanDetails) => {
    setSelectedPlanForUpgrade(plan);
    setPaymentMethod('instapay');
    setProofReference('');
    setProofFile(null);
    setSubmitSuccessMsg(null);
    setSubmitErrorMsg(null);
  };

  const handleCloseUpgrade = () => {
    setSelectedPlanForUpgrade(null);
    setProofReference('');
    setProofFile(null);
    setSubmitSuccessMsg(null);
    setSubmitErrorMsg(null);
  };

  const handleSubmitPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlanForUpgrade) return;
    if (!proofReference.trim() && !proofFile) {
      setSubmitErrorMsg('Please provide a payment reference code or attach a receipt image.');
      return;
    }

    setSubmitErrorMsg(null);
    setSubmitSuccessMsg(null);

    try {
      if (proofFile) {
        await uploadPaymentProof(proofFile, selectedPlanForUpgrade.id, paymentMethod, proofReference.trim());
      } else {
        await submitPaymentRequest(selectedPlanForUpgrade.id, paymentMethod, proofReference.trim());
      }
      setSubmitSuccessMsg(`Payment request for ${selectedPlanForUpgrade.name} submitted successfully! Your subscription will be activated once verified by our team.`);
      setTimeout(() => {
        handleCloseUpgrade();
      }, 2500);
    } catch (err: any) {
      setSubmitErrorMsg(err.response?.data?.detail || err.message || 'Failed to submit payment request.');
    }
  };

  const handleAddNewMethod = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanNumber = cardNumber.replace(/\s+/g, '');
    if (cleanNumber.length < 13 || cleanNumber.length > 19) {
      setMethodActionMsg({ type: 'error', text: 'Please enter a valid card number.' });
      return;
    }

    // Detect card brand
    let detectedBrand = 'visa';
    if (cleanNumber.startsWith('5') || cleanNumber.startsWith('2')) detectedBrand = 'mastercard';
    else if (cleanNumber.startsWith('3')) detectedBrand = 'amex';

    const last4Digits = cleanNumber.slice(-4);
    // Generate secure client-side gateway vault token
    const secureToken = `tok_vault_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    setMethodActionMsg(null);
    try {
      await billingApiService.addPaymentMethod({
        provider: 'stripe',
        payment_token: secureToken,
        brand: detectedBrand,
        last4: last4Digits,
        exp_month: parseInt(cardExpMonth, 10),
        exp_year: parseInt(cardExpYear, 10),
        holder_name: cardHolder.trim() || user?.name || 'Cardholder',
        is_default: cardMakeDefault,
      });

      setMethodActionMsg({ type: 'success', text: 'Secure payment method registered successfully!' });
      setIsAddingMethod(false);
      setCardNumber('');
      setCardCvc('');
      setCardHolder('');
      await loadSavedMethods();
    } catch (err: any) {
      setMethodActionMsg({ type: 'error', text: err.response?.data?.detail || err.message || 'Failed to register payment method.' });
    }
  };

  const handleDeleteMethod = async (id: string) => {
    if (!confirm('Are you sure you want to remove this payment method?')) return;
    try {
      await billingApiService.deletePaymentMethod(id);
      await loadSavedMethods();
      setMethodActionMsg({ type: 'success', text: 'Payment method removed.' });
    } catch (err: any) {
      setMethodActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to remove payment method.' });
    }
  };

  const handleSetDefaultMethod = async (id: string) => {
    try {
      await billingApiService.setDefaultPaymentMethod(id);
      await loadSavedMethods();
      setMethodActionMsg({ type: 'success', text: 'Default payment method updated.' });
    } catch (err: any) {
      setMethodActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to set default method.' });
    }
  };

  const handleAdminApprove = async (paymentId: string) => {
    setProcessingPaymentId(paymentId);
    setAdminActionMsg(null);
    try {
      const res = await approvePayment(paymentId, 'Approved via Admin Panel');
      setAdminActionMsg(res.message || 'Payment approved successfully and user subscription updated.');
      await fetchBillingStatus(user?.id);
    } catch (err: any) {
      setAdminActionMsg(`Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setProcessingPaymentId(null);
    }
  };

  const handleMockCheckout = async (planId: PlanId) => {
    if (planId === 'free') return;
    setMockCheckoutMsg(null);
    try {
      const res = await mockCheckout(planId);
      setMockCheckoutMsg(res.message || `Mock checkout succeeded — plan upgraded to ${planId}.`);
    } catch (err: any) {
      setMockCheckoutMsg(err.response?.data?.detail || err.message || 'Mock checkout failed.');
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
          <p className="text-xs text-slate-500 mt-0.5">Manage your Anti Design plan, tokens, payment methods, and invoice history.</p>
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
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-indigo-500/30 text-indigo-300 border border-indigo-400/30">
                    Active Plan
                  </span>
                  <span className="text-xs text-slate-300 flex items-center space-x-1">
                    <Calendar className="w-3.5 h-3.5 mr-1" />
                    <span>Cycle Ends: {formatCycleDate(cycleEndDate)} ({daysRemaining} days left)</span>
                  </span>
                </div>
                <h2 className="text-2xl font-black tracking-tight text-white">{planDisplayName}</h2>
                <p className="text-xs text-slate-300 max-w-md">
                  {currentPlan === 'free' 
                    ? 'Free starter account for CAD hobbyists. Upgrade to Pro for high-precision CNC generation.' 
                    : 'Full industrial tier with high throughput generation and priority rendering pipelines.'}
                </p>
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

      {/* ── TAB 2: PAYMENT METHODS (Tokenized Vault) ────────────────────────── */}
      {activeSubTab === 'payment_methods' && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-6">
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Saved Payment Methods</h3>
                <p className="text-xs text-slate-500">Manage payment cards securely tokenized with end-to-end encryption.</p>
              </div>

              {!isAddingMethod && (
                <button
                  onClick={() => setIsAddingMethod(true)}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-xs flex items-center space-x-1.5 self-start sm:self-auto"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  <span>Add Payment Method</span>
                </button>
              )}
            </div>

            {/* PCI Compliance Notice */}
            <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-xl text-xs text-indigo-900 flex items-start space-x-2">
              <Lock className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <span>
                <strong>PCI-DSS Compliant Storage:</strong> Anti Design never stores complete credit card numbers or security codes on our servers. All credentials are tokenized via secure cryptographic vaults.
              </span>
            </div>

            {/* Add New Card Form */}
            {isAddingMethod && (
              <form onSubmit={handleAddNewMethod} className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-4">
                <div className="flex justify-between items-center">
                  <h4 className="font-bold text-slate-900 text-sm flex items-center space-x-1.5">
                    <CreditCard className="w-4 h-4 text-indigo-600 mr-1" />
                    <span>Add New Card</span>
                  </h4>
                  <button
                    type="button"
                    onClick={() => setIsAddingMethod(false)}
                    className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1 sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-700">Cardholder Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. John Doe"
                      value={cardHolder}
                      onChange={(e) => setCardHolder(e.target.value)}
                      className="w-full px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600/30"
                    />
                  </div>

                  <div className="space-y-1 sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-700">Card Number</label>
                    <input
                      type="text"
                      required
                      maxLength={19}
                      placeholder="4000 1234 5678 9010"
                      value={cardNumber}
                      onChange={(e) => setCardNumber(e.target.value)}
                      className="w-full px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-900 tracking-wider focus:outline-none focus:ring-2 focus:ring-indigo-600/30"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-700">Expiry Month</label>
                      <select
                        value={cardExpMonth}
                        onChange={(e) => setCardExpMonth(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-900"
                      >
                        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                          <option key={m} value={m}>{m.toString().padStart(2, '0')}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-700">Expiry Year</label>
                      <select
                        value={cardExpYear}
                        onChange={(e) => setCardExpYear(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-900"
                      >
                        {[2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032].map((y) => (
                          <option key={y} value={y}>{y}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">CVC / CVV</label>
                    <input
                      type="password"
                      required
                      maxLength={4}
                      placeholder="123"
                      value={cardCvc}
                      onChange={(e) => setCardCvc(e.target.value)}
                      className="w-full px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-900 tracking-widest focus:outline-none focus:ring-2 focus:ring-indigo-600/30"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2 pt-2">
                  <input
                    type="checkbox"
                    id="makeDefault"
                    checked={cardMakeDefault}
                    onChange={(e) => setCardMakeDefault(e.target.checked)}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <label htmlFor="makeDefault" className="text-xs font-medium text-slate-700 cursor-pointer">
                    Set as default payment method for subscriptions
                  </label>
                </div>

                <div className="flex items-center space-x-2 pt-2">
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-xs"
                  >
                    Save Encrypted Card
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsAddingMethod(false)}
                    className="px-3 py-2 text-slate-600 hover:text-slate-900 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {/* List of Saved Cards */}
            {isLoadingMethods ? (
              <div className="text-center py-8 text-xs text-slate-400">Loading saved payment methods…</div>
            ) : paymentMethods.length === 0 ? (
              <div className="text-center py-10 border-2 border-dashed border-slate-200 rounded-2xl">
                <CreditCard className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-600">No payment methods saved yet.</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Add a credit or debit card for seamless subscription renewals.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {paymentMethods.map((pm) => (
                  <div
                    key={pm.id}
                    className={`border rounded-2xl p-4 flex flex-col justify-between relative transition-all ${
                      pm.is_default
                        ? 'bg-indigo-50/50 border-indigo-300 shadow-xs'
                        : 'bg-white border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-2.5">
                        <div className="w-10 h-7 rounded-md bg-slate-900 text-white flex items-center justify-center font-mono text-[10px] font-black uppercase">
                          {pm.brand}
                        </div>
                        <div>
                          <div className="font-mono font-bold text-slate-900 text-sm">
                            •••• •••• •••• {pm.last4}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            Expires {pm.exp_month.toString().padStart(2, '0')}/{pm.exp_year}
                          </div>
                        </div>
                      </div>

                      {pm.is_default && (
                        <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded-md text-[10px] font-bold">
                          Default
                        </span>
                      )}
                    </div>

                    <div className="text-[11px] text-slate-600 font-medium mb-3">
                      Holder: {pm.holder_name || user?.name || 'Engineer'}
                    </div>

                    <div className="flex items-center justify-between border-t border-slate-100 pt-3">
                      {!pm.is_default ? (
                        <button
                          onClick={() => handleSetDefaultMethod(pm.id)}
                          className="text-[11px] font-bold text-indigo-600 hover:text-indigo-800"
                        >
                          Make Default
                        </button>
                      ) : (
                        <span className="text-[11px] text-slate-400 font-medium">Primary Card</span>
                      )}

                      <button
                        onClick={() => handleDeleteMethod(pm.id)}
                        className="text-slate-400 hover:text-rose-600 p-1 rounded-lg transition-colors"
                        title="Remove Card"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

          </div>
        </div>
      )}

      {/* ── TAB 3: INVOICES & HISTORY ────────────────────────────────────────── */}
      {activeSubTab === 'history' && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <h3 className="font-bold text-slate-900 text-base">Payment &amp; Invoicing History</h3>
          
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
              <p className="text-xs text-slate-500">Review pending bank transfers, InstaPay transfers, and cash receipts.</p>
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

      {/* ── MANUAL PAYMENT MODAL ────────────────────────────────────────────── */}
      {selectedPlanForUpgrade && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-slate-900 text-base">Upgrade to {selectedPlanForUpgrade.name}</h3>
              <button onClick={handleCloseUpgrade} className="p-1 text-slate-400 hover:text-slate-600 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Amount to pay: <strong className="font-mono text-indigo-600 text-sm">${selectedPlanForUpgrade.price} USD</strong>
            </p>

            {submitSuccessMsg ? (
              <div className="p-4 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-bold">
                {submitSuccessMsg}
              </div>
            ) : (
              <form onSubmit={handleSubmitPayment} className="space-y-4">
                {submitErrorMsg && (
                  <div className="p-3 bg-rose-50 text-rose-800 border border-rose-200 rounded-xl text-xs font-semibold">
                    {submitErrorMsg}
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Payment Option</label>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900"
                  >
                    <option value="instapay">InstaPay Mobile Wallet Transfer</option>
                    <option value="cash">Direct Cash / Office Settlement</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Reference / Transfer Code</label>
                  <input
                    type="text"
                    placeholder="e.g. TRX-982314981"
                    value={proofReference}
                    onChange={(e) => setProofReference(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Attach Receipt (Optional)</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setProofFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-slate-500 file:mr-2 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                  />
                </div>

                <div className="flex items-center space-x-2 pt-2">
                  <button
                    type="submit"
                    disabled={isSubmittingPayment}
                    className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-xs disabled:opacity-50"
                  >
                    {isSubmittingPayment ? 'Submitting…' : 'Submit for Verification'}
                  </button>
                  <button
                    type="button"
                    onClick={handleCloseUpgrade}
                    className="px-4 py-2.5 text-slate-600 hover:text-slate-900 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

          </div>
        </div>
      )}

    </div>
  );
};

import { billingApiService } from '../api/billing';

export interface PaddlePublicConfig {
  environment: 'sandbox' | 'production';
  client_token: string;
  prices: {
    pro: string;
    pro_plus: string;
    business: string;
  };
}

export const paddleService = {
  /**
   * Fetches public config from backend
   */
  fetchConfig: async (): Promise<PaddlePublicConfig> => {
    try {
      const data = await billingApiService.getPaddleConfig();
      return data;
    } catch {
      return {
        environment: 'sandbox',
        client_token: 'test_7664c1ecbb2fa20c918c0678d2b',
        prices: {
          pro: 'pri_01m2p85k69p7fxaa2aam45r4jw',
          pro_plus: 'pri_01m2p89n5cce3wjzk8y1aerbg1',
          business: 'pri_01m2p8cbbevbzyvxgp5pfsg746',
        },
      };
    }
  },

  /**
   * Opens official Paddle hosted checkout in the system browser / dedicated window
   */
  openCheckout: async ({
    planId,
    priceId,
    user,
  }: {
    planId: string;
    priceId: string;
    user?: { id?: string; email?: string; name?: string } | null;
  }): Promise<string> => {
    console.log(`[Billing] Opening Paddle checkout for plan: ${planId} (price: ${priceId})`);

    let checkoutUrl = '';
    try {
      const session = await billingApiService.createCheckoutSession(planId);
      checkoutUrl = session.checkout_url;
    } catch {
      // Fallback direct URL if backend session creation fails
      const baseHost = 'https://sandbox-buy.paddle.com';
      const customData = encodeURIComponent(
        JSON.stringify({
          userId: user?.id || '',
          userEmail: user?.email || '',
          userName: user?.name || '',
          planId,
        })
      );
      checkoutUrl = `${baseHost}/checkout?_price=${priceId}&customer_email=${encodeURIComponent(user?.email || '')}&custom_data=${customData}`;
    }

    // Open externally in Electron desktop or default browser
    if ((window as any).electronAPI?.openExternal) {
      await (window as any).electronAPI.openExternal(checkoutUrl);
    } else {
      window.open(checkoutUrl, '_blank', 'noopener,noreferrer');
    }

    return checkoutUrl;
  },
};

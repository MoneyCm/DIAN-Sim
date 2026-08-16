import stripe
import streamlit as st
import os

class StripeService:
    """Servicio para gestionar pagos y suscripciones con Stripe mikey v4.0"""
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        if not cls._initialized:
            api_key = st.secrets.get("stripe", {}).get("api_key") or os.getenv("STRIPE_API_KEY")
            if api_key:
                stripe.api_key = api_key
                cls._initialized = True
                return True
            return False
        return True

    @staticmethod
    def create_checkout_session(user_email, user_id):
        """Crea una sesión de pago para suscripción Pro"""
        if not StripeService.initialize():
            return None
            
        price_id = st.secrets.get("stripe", {}).get("pro_price_id")
        success_url = st.secrets.get("stripe", {}).get("success_url")
        cancel_url = st.secrets.get("stripe", {}).get("cancel_url")
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=user_email,
                metadata={
                    'user_id': user_id
                }
            )
            return session.url
        except Exception as e:
            print(f"Error creating Stripe session: {type(e).__name__}")
            return None

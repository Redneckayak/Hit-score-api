"""
Authentication and subscription configuration for MLB Hit Score Predictor
"""
import streamlit_authenticator as stauth
import yaml
import bcrypt
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import paypalrestsdk

class AuthConfig:
    """Manages user authentication and subscription data"""
    
    def __init__(self):
        self.users_file = 'data/users.json'
        self.subscriptions_file = 'data/subscriptions.json'
        self.config_file = 'data/auth_config.yaml'
        self.ensure_data_files()
    
    def ensure_data_files(self):
        """Create data files if they don't exist"""
        os.makedirs('data', exist_ok=True)
        
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({}, f)
        
        if not os.path.exists(self.subscriptions_file):
            with open(self.subscriptions_file, 'w') as f:
                json.dump({}, f)
        
        if not os.path.exists(self.config_file):
            self.create_auth_config()
    
    def create_auth_config(self):
        """Create authentication configuration"""
        config = {
            'credentials': {
                'usernames': {}
            },
            'cookie': {
                'name': 'mlb_predictor_auth',
                'key': 'mlb_random_signature_key_123456789',
                'expiry_days': 30
            },
            'preauthorized': []
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f)
    
    def load_config(self) -> Dict:
        """Load authentication configuration"""
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def save_config(self, config: Dict):
        """Save authentication configuration"""
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f)
    
    def register_user(self, username: str, email: str, password: str, name: str = None) -> bool:
        """Register a new user"""
        try:
            config = self.load_config()
            
            # Check if user already exists
            if username in config['credentials']['usernames']:
                return False
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Add user to config
            config['credentials']['usernames'][username] = {
                'email': email,
                'name': name or username,
                'password': hashed_password,
                'registered_date': datetime.now().isoformat()
            }
            
            self.save_config(config)
            
            # Initialize subscription data
            self.init_user_subscription(username, email)
            
            return True
            
        except Exception as e:
            print(f"Registration error: {e}")
            return False
    
    def init_user_subscription(self, username: str, email: str):
        """Initialize user subscription data"""
        try:
            with open(self.subscriptions_file, 'r') as f:
                subscriptions = json.load(f)
            
            subscriptions[username] = {
                'email': email,
                'subscription_status': 'trial',
                'trial_start': datetime.now().isoformat(),
                'trial_end': (datetime.now() + timedelta(days=3)).isoformat(),
                'subscription_start': None,
                'subscription_end': None,
                'payment_id': None,
                'auto_renew': False
            }
            
            with open(self.subscriptions_file, 'w') as f:
                json.dump(subscriptions, f, indent=2)
                
        except Exception as e:
            print(f"Subscription init error: {e}")
    
    def get_user_subscription(self, username: str) -> Optional[Dict]:
        """Get user subscription information"""
        try:
            with open(self.subscriptions_file, 'r') as f:
                subscriptions = json.load(f)
            
            return subscriptions.get(username)
            
        except Exception as e:
            print(f"Subscription lookup error: {e}")
            return None
    
    def is_subscription_active(self, username: str) -> bool:
        """Check if user has active subscription"""
        subscription = self.get_user_subscription(username)
        if not subscription:
            return False
        
        now = datetime.now()
        
        # Check trial period
        if subscription['subscription_status'] == 'trial':
            trial_end = datetime.fromisoformat(subscription['trial_end'])
            return now <= trial_end
        
        # Check paid subscription
        if subscription['subscription_status'] == 'active':
            if subscription['subscription_end']:
                sub_end = datetime.fromisoformat(subscription['subscription_end'])
                return now <= sub_end
        
        return False
    
    def update_subscription(self, username: str, payment_id: str, months: int = 1):
        """Update user subscription after successful payment"""
        try:
            with open(self.subscriptions_file, 'r') as f:
                subscriptions = json.load(f)
            
            if username in subscriptions:
                now = datetime.now()
                subscription_end = now + timedelta(days=30 * months)
                
                subscriptions[username].update({
                    'subscription_status': 'active',
                    'subscription_start': now.isoformat(),
                    'subscription_end': subscription_end.isoformat(),
                    'payment_id': payment_id,
                    'last_payment': now.isoformat(),
                    'auto_renew': True
                })
                
                with open(self.subscriptions_file, 'w') as f:
                    json.dump(subscriptions, f, indent=2)
                
                return True
            
        except Exception as e:
            print(f"Subscription update error: {e}")
        
        return False

class PayPalManager:
    """Manages PayPal payments and subscriptions"""
    
    def __init__(self):
        self.monthly_price = 29.99  # $29.99/month
        self.setup_paypal()
    
    def setup_paypal(self):
        """Configure PayPal SDK"""
        # PayPal configuration will be set using environment variables
        paypalrestsdk.configure({
            "mode": os.getenv("PAYPAL_MODE", "sandbox"),  # sandbox or live
            "client_id": os.getenv("PAYPAL_CLIENT_ID", ""),
            "client_secret": os.getenv("PAYPAL_CLIENT_SECRET", "")
        })
    
    def create_payment(self, username: str, email: str, amount: float = None) -> Optional[str]:
        """Create PayPal payment"""
        if amount is None:
            amount = self.monthly_price
        
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": f"http://localhost:5000/payment/success?username={username}",
                    "cancel_url": "http://localhost:5000/payment/cancel"
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": "MLB Hit Score Predictor - Monthly Subscription",
                            "sku": "mlb_monthly",
                            "price": str(amount),
                            "currency": "USD",
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": "USD"
                    },
                    "description": f"Monthly subscription for {email}"
                }]
            })
            
            if payment.create():
                # Find approval URL
                for link in payment.links:
                    if link.rel == "approval_url":
                        return link.href
            else:
                print(f"PayPal payment creation error: {payment.error}")
            
        except Exception as e:
            print(f"PayPal error: {e}")
        
        return None
    
    def execute_payment(self, payment_id: str, payer_id: str) -> bool:
        """Execute approved PayPal payment"""
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            
            if payment.execute({"payer_id": payer_id}):
                return True
            else:
                print(f"PayPal execution error: {payment.error}")
        
        except Exception as e:
            print(f"PayPal execution error: {e}")
        
        return False
    
    def get_payment_details(self, payment_id: str) -> Optional[Dict]:
        """Get PayPal payment details"""
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            return {
                'id': payment.id,
                'state': payment.state,
                'amount': payment.transactions[0].amount.total,
                'currency': payment.transactions[0].amount.currency,
                'payer_email': payment.payer.payer_info.email if hasattr(payment.payer, 'payer_info') else None
            }
        except Exception as e:
            print(f"PayPal details error: {e}")
            return None
"""
Authentication pages for MLB Hit Score Predictor
"""
import streamlit as st
import streamlit_authenticator as stauth
from auth_config import AuthConfig, PayPalManager
import yaml
from datetime import datetime, timedelta
import re

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, ""

def show_registration_page():
    """Display user registration page"""
    st.title("🔐 Register for MLB Hit Score Predictor")
    st.markdown("**Get access to professional-grade MLB hitting predictions**")
    
    with st.form("registration_form"):
        st.subheader("Create Your Account")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name")
            username = st.text_input("Username")
        with col2:
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
        
        confirm_password = st.text_input("Confirm Password", type="password")
        
        # Terms and conditions
        terms_accepted = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        
        submitted = st.form_submit_button("Create Account", use_container_width=True)
        
        if submitted:
            # Validation
            if not all([name, username, email, password]):
                st.error("Please fill in all fields")
                return
            
            if not validate_email(email):
                st.error("Please enter a valid email address")
                return
            
            is_valid, password_error = validate_password(password)
            if not is_valid:
                st.error(password_error)
                return
            
            if password != confirm_password:
                st.error("Passwords do not match")
                return
            
            if not terms_accepted:
                st.error("Please accept the Terms of Service")
                return
            
            # Register user
            auth_config = AuthConfig()
            if auth_config.register_user(username, email, password, name):
                st.success("Registration successful! You now have a 3-day free trial.")
                st.info("Please log in to access your account")
                st.rerun()
            else:
                st.error("Username already exists. Please choose a different username.")

def show_login_page():
    """Display login page with subscription management"""
    auth_config = AuthConfig()
    config = auth_config.load_config()
    
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    
    # Login widget
    name, authentication_status, username = authenticator.login()
    
    if authentication_status == False:
        st.error('Username/password is incorrect')
    elif authentication_status == None:
        st.warning('Please enter your username and password')
        
        # Registration option
        st.markdown("---")
        st.markdown("### Don't have an account?")
        if st.button("Register for Free Trial", use_container_width=True):
            st.session_state['show_registration'] = True
            st.rerun()
    
    return name, authentication_status, username, authenticator

def show_subscription_page(username: str):
    """Display subscription management page"""
    st.title("💳 Subscription Management")
    
    auth_config = AuthConfig()
    subscription = auth_config.get_user_subscription(username)
    
    if not subscription:
        st.error("Subscription information not found")
        return
    
    # Current subscription status
    st.subheader("Current Subscription Status")
    
    is_active = auth_config.is_subscription_active(username)
    status = subscription['subscription_status']
    
    if status == 'trial':
        trial_end = datetime.fromisoformat(subscription['trial_end'])
        days_left = (trial_end - datetime.now()).days
        
        if is_active:
            st.success(f"Free Trial Active - {days_left} days remaining")
            st.info(f"Trial expires: {trial_end.strftime('%B %d, %Y')}")
        else:
            st.error("Free trial has expired")
    
    elif status == 'active':
        if subscription['subscription_end']:
            sub_end = datetime.fromisoformat(subscription['subscription_end'])
            days_left = (sub_end - datetime.now()).days
            
            if is_active:
                st.success(f"Premium Subscription Active - {days_left} days remaining")
                st.info(f"Next billing: {sub_end.strftime('%B %d, %Y')}")
            else:
                st.error("Subscription has expired")
    else:
        st.error("No active subscription")
    
    # Subscription options
    st.markdown("---")
    st.subheader("Subscription Plans")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Free Trial**
        - 3 days access
        - All prediction features
        - Performance tracking
        - Top 3 daily picks
        """)
        
        if status == 'trial' and is_active:
            st.info("Currently Active")
        else:
            st.error("Expired or Used")
    
    with col2:
        st.markdown("""
        **Premium Monthly**
        - **$29.99/month**
        - Unlimited access
        - All prediction features
        - Performance tracking
        - Priority support
        """)
        
        if status == 'active' and is_active:
            st.success("Currently Active")
        else:
            if st.button("Subscribe for $29.99/month", use_container_width=True, type="primary"):
                initiate_payment(username, subscription['email'])

def initiate_payment(username: str, email: str):
    """Initiate PayPal payment process"""
    paypal_manager = PayPalManager()
    
    with st.spinner("Setting up PayPal payment..."):
        approval_url = paypal_manager.create_payment(username, email)
        
        if approval_url:
            st.success("Payment setup successful!")
            st.markdown(f"**[Click here to complete payment via PayPal]({approval_url})**")
            st.info("You will be redirected to PayPal to complete your payment securely.")
        else:
            st.error("Payment setup failed. Please try again or contact support.")

def check_subscription_access(username: str) -> bool:
    """Check if user has access to premium features"""
    auth_config = AuthConfig()
    return auth_config.is_subscription_active(username)

def show_access_denied():
    """Show access denied page for expired subscriptions"""
    st.title("🚫 Access Restricted")
    st.error("Your subscription has expired or you don't have an active subscription.")
    
    st.markdown("### Subscribe to continue accessing MLB Hit Score Predictor")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Subscription Options", use_container_width=True, type="primary"):
            st.session_state['show_subscription'] = True
            st.rerun()
    
    with col2:
        if st.button("Contact Support", use_container_width=True):
            st.markdown("**Support Email:** support@hitscoresapp.com")

def handle_payment_callback():
    """Handle PayPal payment callback"""
    query_params = st.experimental_get_query_params()
    
    if 'payment_id' in query_params and 'payer_id' in query_params:
        payment_id = query_params['payment_id'][0]
        payer_id = query_params['payer_id'][0]
        username = query_params.get('username', [None])[0]
        
        if username:
            paypal_manager = PayPalManager()
            auth_config = AuthConfig()
            
            # Execute payment
            if paypal_manager.execute_payment(payment_id, payer_id):
                # Update subscription
                if auth_config.update_subscription(username, payment_id):
                    st.success("Payment successful! Your subscription has been activated.")
                    st.balloons()
                else:
                    st.error("Payment processed but subscription update failed. Please contact support.")
            else:
                st.error("Payment execution failed. Please try again.")
        else:
            st.error("Invalid payment callback. Please contact support.")

def show_user_profile(username: str, name: str):
    """Show user profile information"""
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Welcome, {name}**")
    
    auth_config = AuthConfig()
    subscription = auth_config.get_user_subscription(username)
    
    if subscription:
        status = subscription['subscription_status']
        if status == 'trial':
            trial_end = datetime.fromisoformat(subscription['trial_end'])
            days_left = max(0, (trial_end - datetime.now()).days)
            st.sidebar.info(f"Trial: {days_left} days left")
        elif status == 'active':
            st.sidebar.success("Premium Active")
    
    if st.sidebar.button("Manage Subscription"):
        st.session_state['show_subscription'] = True
        st.rerun()
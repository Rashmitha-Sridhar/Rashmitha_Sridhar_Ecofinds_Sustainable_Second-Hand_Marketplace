EcoFinds – Sustainable Second-Hand Marketplace

EcoFinds is a Flask-based web application designed to promote sustainable consumption by enabling users to buy, sell, and manage second-hand products easily. The platform focuses on providing a simple, user-friendly interface with essential marketplace features like product listings, a shopping cart, and order management.

🚀 Features

User Authentication:

Signup and login functionality.

Secure user session handling.

Product Management:

Add, edit, and delete products.

View product details and track inventory.

Shopping Cart:

Add products to cart.

Place orders with a smooth checkout process.

Order History:

Track previous purchases.

Get confirmation on successful orders.

User Dashboard:

Personalized dashboard with quick links to products and orders.

🛠️ Tech Stack
Layer	Technology
Backend	Python (Flask Framework)
Frontend	HTML5, CSS3, Jinja2 Templates
Database	SQLite / Any SQL Database
Other	Flask session management, REST principles
📂 Project Structure
Rashmitha_Sridhar_Ecofinds_Sustainable_Second-Hand_Marketplace/
└── echofinds/
    ├── __pycache__/               # Compiled Python files
    ├── static/                    # Static assets (CSS, JS, Images)
    │   └── css/
    │       └── styles.css
    ├── templates/                 # HTML templates (Jinja2)
    │   ├── add_product.html
    │   ├── cart.html
    │   ├── dashboard.html
    │   ├── edit_product.html
    │   ├── login.html
    │   ├── order_success.html
    │   ├── previous_purchases.html
    │   ├── product_detail.html
    │   ├── products.html
    │   ├── profile.html
    │   └── signup.html
    ├── app.py                     # Main Flask application
    └── db.py                      # Database setup and logic

⚙️ Installation and Setup

Follow these steps to run the project locally:

Clone the repository:

git clone https://github.com/Rashmitha-Sridhar/Rashmitha_Sridhar_Ecofinds_Sustainable_Second-Hand_Marketplace.git
cd Rashmitha_Sridhar_Ecofinds_Sustainable_Second-Hand_Marketplace/echofinds


Create a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install dependencies:

pip install -r requirements.txt


Run the app:

flask run


The app will start on: http://127.0.0.1:5000/

 Screens (Optional)

(Add screenshots or GIFs of your app’s dashboard, product listings, and cart here.)

Future Enhancements

Product search and filters.

Payment gateway integration.

User profile image upload.

Advanced analytics dashboard for sellers.

Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your changes

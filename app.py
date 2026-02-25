from asset_manager import create_app, db
from seed import seed_database
app = create_app()

if __name__ == '__main__':

    with app.app_context():
        db.create_all()
        seed_database()

    app.run(debug=True, port=5000)

import os
import mysql.connector

db_config = {
    'host': os.getenv('DB_HOST', 'mysql'),
    'user': os.getenv('DB_USER', 'joke_user'),
    'password': os.getenv('DB_PASSWORD', 'joke_pass123'),
    'database': os.getenv('DB_NAME', 'jokes_db'),
    'port': int(os.getenv('DB_PORT', '3306'))
}

jokes = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "What do you call a fake noodle? An impasta!",
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "Did you hear about the restaurant on the moon? Great food, no atmosphere.",
    "Why don't eggs tell jokes? They'd crack each other up!",
    "I used to hate facial hair, but then it grew on me.",
    "What do you call a bear with no teeth? A gummy bear!",
    "Why did the bicycle fall over? Because it was two tired!",
    "What do you call cheese that isn't yours? Nacho cheese!",
    "I'm afraid for the calendar. Its days are numbered.",
    "What's the best time to go to the dentist? Tooth hurty!",
    "How do you organize a space party? You planet!",
    "Why can't you hear a pterodactyl go to the bathroom? Because the P is silent!",
    "What did the ocean say to the beach? Nothing, it just waved.",
    "Why do chicken coops only have two doors? Because if they had four, they'd be chicken sedans!",
    "What's orange and sounds like a parrot? A carrot!",
    "How does a penguin build its house? Igloos it together!",
    "Why did the math book look so sad? Because it had too many problems.",
    "What do you call a dog magician? A labracadabrador!",
    "Why don't skeletons fight each other? They don't have the guts.",
    "What did the left eye say to the right eye? Between you and me, something smells.",
    "Why did the coffee file a police report? It got mugged!",
    "What do you call a pile of cats? A meowtain!",
    "How do you make a tissue dance? You put a little boogie in it!",
    "Why did the golfer bring two pairs of pants? In case he got a hole in one!",
    "What's brown and sticky? A stick!",
    "Why don't oysters donate to charity? Because they're shellfish!",
    "What do you call a sleeping bull? A bulldozer!",
    "Why did the tomato turn red? Because it saw the salad dressing!",
    "What do you call a fish wearing a crown? A king fish!",
    "Why did the cookie go to the doctor? Because it felt crumbly!",
    "What do you call a cow with no legs? Ground beef!",
    "Why did the picture go to jail? Because it was framed!",
    "What did one wall say to the other wall? I'll meet you at the corner!",
    "Why don't scientists trust stairs? Because they're always up to something!",
    "What do you call a belt made of watches? A waist of time!",
    "Why did the stadium get hot after the game? All the fans left!",
    "What do you call a snowman in July? A puddle!",
    "Why did the computer go to the doctor? Because it had a virus!",
    "What do you call a lazy kangaroo? A pouch potato!",
    "Why did the banana go to the doctor? Because it wasn't peeling well!",
    "What do you call a group of unorganized cats? A cat-astrophe!",
    "Why did the mushroom go to the party? Because he was a fungi!",
    "What do you call a deer with no eyes? No eye deer!",
    "Why did the skeleton go to the party alone? He had no body to go with him!",
    "What do you call a factory that makes okay products? A satisfactory!",
    "Why did the invisible man turn down the job offer? He couldn't see himself doing it!",
    "What do you call a sleeping dinosaur? A dino-snore!"
]

EXPECTED_JOKE_COUNT = 50

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Check if table exists and count jokes
    cursor.execute("SHOW TABLES LIKE 'jokes'")
    table_exists = cursor.fetchone() is not None

    should_initialize = False

    if table_exists:
        cursor.execute("SELECT COUNT(*) FROM jokes")
        count = cursor.fetchone()[0]

        if count != EXPECTED_JOKE_COUNT:
            print(f"⚠️  Found {count} jokes, but expected {EXPECTED_JOKE_COUNT}.")
            print("🗑️  Dropping table and reinitializing...")
            cursor.execute("DROP TABLE jokes")
            should_initialize = True
        else:
            print(f"✅ Database already contains {count} jokes. No action needed.")
    else:
        print("📋 Table 'jokes' does not exist. Creating and initializing...")
        should_initialize = True

    if should_initialize:
        # Create table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jokes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                text TEXT NOT NULL
            )
        ''')

        # Insert jokes
        for joke in jokes:
            cursor.execute("INSERT INTO jokes (text) VALUES (%s)", (joke,))

        conn.commit()
        print(f"✅ Successfully inserted {len(jokes)} jokes into the database!")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Error initializing database: {e}")
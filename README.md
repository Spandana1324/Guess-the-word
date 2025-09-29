# Guess-the-word


1)Project Overview
WordQuest is a word-guessing game built using Python (Flask) and SQLite.  

2)It has two user roles:
1. Admin – Manage words (add, edit, delete) and view player reports.  
2. Player – Register, log in, and play the word-guessing game.

3)Features
- User authentication (registration & login)  
- Validation rules:  
  - Username: at least 5 characters (mix of upper/lowercase)  
  - Password: at least 5 characters, must include letters, numbers, and one special character (`$`, `%`, `*`, `@`)  
- Stores at least 20 words in the database  
- Tracks scores and attempts  
- Admin dashboard for reports  
  

# 🎓 Recommendation System for Books

> **Thesis project in Information Technology**  
> Author: **Daniil Skrynnyk**

---

An intelligent book recommendation system built with Python, Flask, and machine learning. The system learns user preferences over time using adaptive algorithms and improves recommendations dynamically.

---

## 🚀 Features

- 🤖 Hybrid recommendation system: content-based, collaborative, and genre-based  
- 🧠 Personalized learning using Multi-Armed Bandit algorithm (UCB1)  
- 📊 Admin dashboard with analytics (Bokeh visualizations)  
- 🛠️ Book & genre management via admin panel  
- 🛒 Shopping cart, order history, user roles (admin/user)

---

## 🧠 How the recommender system works

Three main recommendation strategies:

1. **Content-based**: recommends books similar in description (TF-IDF + cosine similarity)  
2. **Collaborative filtering**: recommends what similar users liked (via SVD)  
3. **Genre-based**: recommends books from user's preferred genres

Final recommendations are combined based on strategy weights, which adapt for each user.

---

## 🤔 Simple explanation: how the bandit works

At first, the system doesn’t know what works best for the user. So it shows different types of recommendations.  
If you buy a book recommended by the genre strategy, the system remembers that — and next time, it will use that strategy more.

This is called a multi-armed bandit, like a slot machine with different levers:
- Try all levers first (exploration)  
- See which one gives the most “wins” (purchases)  
- Use the better ones more (exploitation)

Over time, the system learns your preferences — automatically.

---

## 🎰 Advanced: Multi-Armed Bandit with UCB1

Each recommendation strategy is considered an "arm" of the bandit:

- content
- collaborative
- genre

**UCB formula:**  
UCB = average_reward + α × √(ln(N) / nᵢ)

Where:
- `nᵢ` = how many times strategy `i` was used  
- `N` = total number of recommendations shown  
- `α` = confidence parameter (0.75)  
- `reward = 1.0` if the user bought the book

Each time a user buys a book, the strategy that recommended it gets a reward.  
The system updates the weights and uses them to generate better future recommendations.

---

## ⚖️ What are strategy weights?

Each strategy has a dynamic weight — a number between 0 and 1. Example:

```
Content-based     → 0.20  
Collaborative     → 0.50  
Genre-based       → 0.30
```

📌 This means: if 10 recommendations are shown, 5 will be collaborative, 3 genre-based, 2 content-based.

### How weights change:
- Initially, all weights are equal (e.g., 0.33 each)  
- When a book is purchased, the responsible strategy gets rewarded  
- UCB1 updates the weights  
- Weights are saved in the database per user

✅ The more successful a strategy is — the more influence it gets.

---

## 🗂️ Project structure

```
├── main.py                   # Flask app and routes
├── recommender.py           # Recommendation algorithms
├── bandit.py                # Multi-Armed Bandit (UCB1 logic)
├── data_visualization.py    # Bokeh visualizations
├── templates/               # HTML templates
├── static/                  # Book covers and CSS
├── books_db.sqlite          # SQLite database
```

---

## ⚙️ Installation & Run

```bash
git clone https://github.com/Lirdan/recomendation-system.git
cd recomendation-system
pip install -r requirements.txt
python main.py
```

Then open: [http://localhost:5000](http://localhost:5000)  
Make sure the `books_db.sqlite` file exists.

---

## 📊 Admin dashboard

Includes analytics on recommendation performance:

- 📊 Pie chart: how often each strategy is used  
- 📈 Conversion rate: how many purchases per strategy  
- 🔎 CTR: click-through rate per recommendation type

---

## 📎 Author

**Daniil Skrynnyk**  
This project was developed as a diploma thesis in Information Technology.  
[GitHub: @Lirdan](https://github.com/Lirdan)
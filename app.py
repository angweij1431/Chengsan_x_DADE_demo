import streamlit as st
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, _tree
import graphviz
import re

st.set_page_config(page_title="Live AI Mind-Reader", layout="wide")

# --- 1. Load Initial Data & Session State ---
def load_data():
    data = [
        {"name": "Laksa", "is_food": 1, "is_plant_animal": 0, "is_place": 0, "is_legendary": 0},
        {"name": "Merlion", "is_food": 0, "is_plant_animal": 0, "is_place": 1, "is_legendary": 1},
        {"name": "Hainanese Chicken Rice", "is_food": 1, "is_plant_animal": 0, "is_place": 0, "is_legendary": 0},
        {"name": "Marina Bay Sands", "is_food": 0, "is_plant_animal": 0, "is_place": 1, "is_legendary": 0},
        {"name": "Smooth-coated Otter", "is_food": 0, "is_plant_animal": 1, "is_place": 0, "is_legendary": 0},
        {"name": "Chilli Crab", "is_food": 1, "is_plant_animal": 1, "is_place": 0, "is_legendary": 0},
        {"name": "Vanda Miss Joaquim", "is_food": 0, "is_plant_animal": 1, "is_place": 0, "is_legendary": 1},
        {"name": "Sang Nila Utama", "is_food": 0, "is_plant_animal": 0, "is_place": 0, "is_legendary": 1}
    ]
    return pd.DataFrame(data)

if "df" not in st.session_state:
    st.session_state.df = load_data()
if "node_history" not in st.session_state:
    st.session_state.node_history = [0]
if "failed" not in st.session_state:
    st.session_state.failed = False
    
# Dynamic map to translate column keys into human questions
if "question_map" not in st.session_state:
    st.session_state.question_map = {
        "is_food": "Is your item something you can eat or drink?",
        "is_plant_animal": "Is it related to a living plant or animal?",
        "is_place": "Is it a physical location, building, or landmark?",
        "is_legendary": "Is it symbolic, national, or rooted in folklore?"
    }

df = st.session_state.df
features = [c for c in df.columns if c != "name"]
X = df[features]
y = df["name"]

# --- 2. Live Model Training ---
clf = DecisionTreeClassifier(random_state=42)
clf.fit(X, y)
tree = clf.tree_

current_node = st.session_state.node_history[-1]

# --- 3. Helper Functions ---
def is_leaf(node_id):
    return tree.children_left[node_id] == _tree.TREE_LEAF

def get_node_prediction(node_id):
    values = tree.value[node_id][0]
    best_idx = np.argmax(values)
    return clf.classes_[best_idx]

def make_graph(active_node):
    dot = graphviz.Digraph(format="svg")
    dot.attr("node", shape="box", style="rounded,filled", fontsize="10")
    
    def add_nodes(node_id):
        if is_leaf(node_id):
            dot.node(str(node_id), get_node_prediction(node_id), fillcolor="#A8E6CF" if node_id == active_node else "#E0E0E0")
            return
        
        feat_key = features[tree.feature[node_id]]
        # Truncate question for the graph so nodes don't get too wide
        full_question = st.session_state.question_map.get(feat_key, feat_key)
        short_label = (full_question[:25] + '...?') if len(full_question) > 25 else full_question
        
        dot.node(str(node_id), short_label, fillcolor="#FFD3B6" if node_id == active_node else "#F5F5F5")
        
        left = tree.children_left[node_id]
        right = tree.children_right[node_id]
        if left != _tree.TREE_LEAF:
            dot.edge(str(node_id), str(left), label="No")
            add_nodes(left)
        if right != _tree.TREE_LEAF:
            dot.edge(str(node_id), str(right), label="Yes")
            add_nodes(right)

    add_nodes(0)
    return dot

# --- 4. UI Layout & Game Logic ---
st.title("Live Learning AI")
st.caption("Play the game. If the AI is wrong, teach it something new!")
col_game, col_viz = st.columns([1, 1])

with col_game:
    if not st.session_state.failed:
        if is_leaf(current_node):
            prediction = get_node_prediction(current_node)
            st.success(f"**My guess is: {prediction}**")
            
            col1, col2 = st.columns(2)
            if col1.button("You got it!", use_container_width=True):
                st.session_state.node_history = [0]
                st.rerun()
            if col2.button("Wrong!", use_container_width=True):
                st.session_state.failed = True
                st.session_state.wrong_guess = prediction
                st.rerun()
        else:
            feat_idx = tree.feature[current_node]
            feat_key = features[feat_idx]
            # Fetch the actual human-readable question
            question_text = st.session_state.question_map.get(feat_key, f"Does it satisfy: {feat_key}?")
            
            st.markdown(f"### {question_text}")
            col1, col2 = st.columns(2)
            if col1.button("Yes", use_container_width=True):
                st.session_state.node_history.append(tree.children_right[current_node])
                st.rerun()
            if col2.button("No", use_container_width=True):
                st.session_state.node_history.append(tree.children_left[current_node])
                st.rerun()

    # --- 5. The Data Engineering (Learning) Step ---
    if st.session_state.failed:
        st.warning("I need to learn! Let's update my dataset.")
        wrong_guess = st.session_state.wrong_guess
        
        new_item = st.text_input("What were you actually thinking of?")
        new_question = st.text_input(f"Type a Yes/No question where the answer is YES for **{new_item}** and NO for **{wrong_guess}**:", placeholder="e.g., Is it famously spicy?")
        
        if st.button("Train AI"):
            if new_item and new_question:
                # 1. Generate a safe dataframe column key from the text
                new_feature_key = re.sub(r'[^a-z0-9]', '_', new_question.lower())[:20] + f"_{len(features)}"
                
                # 2. Save the human-readable question to the map
                st.session_state.question_map[new_feature_key] = new_question
                
                # 3. Add column and populate data
                st.session_state.df[new_feature_key] = 0
                wrong_guess_row = st.session_state.df[st.session_state.df["name"] == wrong_guess].iloc[0].copy()
                wrong_guess_row["name"] = new_item
                wrong_guess_row[new_feature_key] = 1 
                
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([wrong_guess_row])], ignore_index=True)
                
                st.session_state.failed = False
                st.session_state.node_history = [0]
                st.rerun()

with col_viz:
    st.subheader("Live Model Flowchart")
    st.graphviz_chart(make_graph(current_node), use_container_width=True)
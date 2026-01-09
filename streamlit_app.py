import streamlit as st
import sqlite3
import json
import os
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()

# Configuração da Chave de API
API_KEY = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
MODEL_ID = "gemma-3-27b-it"

# Configuração de Persistência (Cloud vs Local)
IS_CLOUD = os.path.exists("/data")
DB_FILE = "/data/english_quiz.db" if IS_CLOUD else "english_quiz.db"

# --- SYLLABUS (TÓPICOS E NÍVEIS) ---
COURSE_SYLLABUS = {
    "Beginner": [
        "Introducing yourself", "Alphabet + Numbers + Countries", "Ages and Nationalities (To Be)",
        "Possessive Adjectives", "This/That", "Possessive Apostrophe - Possessives – use of ‘s, s’",
        "This/That and These/Those", "Possessive Pronouns", "What do you do?", "What's the time?",
        "Simple Present (Other Verbs) - Affirmative", "Days and Prepositions/Frequency Phrases",
        "Prepositions of Time, including in/on/at", "Simple Present (To Be)", "Simple Present (Other Verbs)",
        "Simple Present (To Be + Other Verbs)", "Short answers (To Be + Other Verbs)", "Open Questions",
        "There is/There are", "Define and Indefinite Articles (a,an,the, some,any)", "Imperatives",
        "Directions", "Prepositions of Place, Position (in front of, behind, between)",
        "Adjectives: Common and Demonstrative + Quantity phrases", "Why and Because", "Have Got/Have",
        "Countable and Uncountable Nouns", "How Much/How Many",
        "Measurements (enough, not enough, too much, too many)",
        "Shopping (verbs, using too, fit, fitting room, try it on...)", "Adjectives: Opinion + Factual",
        "Go + Verb-ing", "Adverbs of Frequency", "How often x When", "Gerunds - Verb + ing: like/hate/love",
        "Expressing preference", "Modals: Can/Can’t", "Regular and Irregular adverbs", "Good and Bad at",
        "Modifying adverbs (really, very, quite)", "Would Like and Want", "Articles and the Zero Article",
        "Objective Pronouns", "GO"
    ],
    "Pre Intermediate": [
        "Simple Present (To Be + Other Verbs)", "Present Continuous - Information Questions",
        "Present Continuous - Yes or No", "Prepositions, Common (Gadgets + Feelings + Place, Time and Movement)",
        "Action verbs x State verbs", "Feelings", "Adjectives ending in -ED / - ING", "Adverbs",
        "Contrasting Routines and Exceptions", "What’s The Matter?", "The Weather", "Comparatives Adjectives",
        "Superlative Adjectives", "Which and What", "Large Numbers", "Simple Past", "Dates – Was Born/Ago",
        "Simple Past (Regular verbs)", "Simple Past (Irregular verbs)", "Modals – Can/Could",
        "Question Words with the Past Simple", "Dealing with job applications", "Subject and Object Questions",
        "Indefinite Pronouns", "Short Questions", "Future with Present Continuous", "Going To", "Will",
        "Going To and Will", "Modals", "Modals - Might/May", "Modals – Should - Advice", "Modals – Have to",
        "Modals – Could", "Present Perfect", "Adverbs - Just, already, yet, never, ever",
        "Desires and Plans - Would Like + Going To", "Speak x Talk / Say x Tell (present and past simple)",
        "Broader Range of Intensifiers", "Comparatives and Superlatives", "Using 'MOST'"
    ],
    "Intermediate": [
        "Prepositions of Place (in, on, by, off) + Prepositional phrases", "Numbers and Statistics",
        "Contact details (at number 32, Park street...)", "Job and Professions (Job or Work)", "Adverbs",
        "Phrasal verbs, extended", "Adjective order", "Fashion styles", "Dependent prepositions", "Collocations",
        "Separable Phrasal Verbs", "Modifiers(Describing and Comparing)", "Adjectives ending in -ED/ -ING",
        "Emphatic DO ( Past Simple / DID)", "Prefixes and Suffixes", "Present Perfect",
        "Present Perfect/Past Simple", "Present Perfect and Modifying Adverbs",
        "Present Perfect Continuous / State Verbs", "Present Perfect / Present Perfect Continuous",
        "Negative Prefixes", "Measurements ( FOOD / DRINKS)", "Reflexive Pronouns", "Gerunds and Infinitives",
        "Simple Verb Patterns", "Collocations ( TAKE )", "Going to", "WILL / GOING TO (PREDICTIONS) / Adverbs+WILL",
        "Modal Verb (MIGHT) Past, Present & Future", "MUST and HAVE TO",
        "Modal Verbs (MIGHT/ COULD) Making Deductions", "Modal Verbs (CAN/ COULD) Requests",
        "Three- Word Phrasal Verbs", "Question Tags with Modal Verbs", "Zero Conditional",
        "Present Simple Passive Voice", "First Conditional", "Subordinate Time Clauses", "Second Conditional",
        "Question Phrases using Gerunds", "First and Second Conditional", "Collocations with GIVE, HOLD and SET",
        "Defining Relative Clauses", "Non Defining Relative Clauses", "Past Continuous",
        "Past Continuous + Past Simple", "Past Simple Passive", "Past Perfect and Past Simple",
        "Common English Idioms", "Narrative Tenses", "Time Adverbs and Phrases", "Reported Speech (Range of Tenses)",
        "Reported Questions", "Indirect Questions", "Wish + Past Tense Verbs"
    ],
    "Advanced": [
        "Action and State Verbs", "Collocations", "Order of Opinion and Fact Adjectives",
        "Jobs and Professions (Preparation)", "Introductory It", "Phrasal Verbs Overview",
        "Past Perfect Continuous", "Modal Verbs for Advice and Opinions", "Degrees of Likelihood",
        "Discourse Markers / Linking Words", "Used to and Would", "Comparing and Contrasting (as.......as)",
        "Double Comparatives", "Formal Discourse Markers", "Generalization", "Passive Voice",
        "Nouns based on Phrasal Verbs", "Hypothetical Situations", "Gerunds after Prepositions",
        "Direct and Indirect Questions", "Verb + Infinitive/ Gerund", "Dependent Prepositions",
        "Double Object Verbs", "Reflexive Pronouns", "Infinitive or -ing /Change or none in meaning",
        "Non Gradable-Adjectives/ Non-Gradable Adverbs", "In Order to / So that", "Third Conditional",
        "Second and Third Conditional", "Should (Ought to) Have / Time Markers (PAST)", "Dependent Prepositions",
        "Few, Little, Fewer, Less, Quite a few/ a bit", "Past Modals ( MAY, MIGHT, COULD)",
        "Modal Verbs of Speculation and Deduction", "Mixed Conditional", "Using -ever",
        "Passive Voice (Reporting)", "Hedging", "Inversions with Adverbials", "Focusing with Clauses",
        "Relative Clauses", "Relative Words", "Modal Verbs (Future)", "Modal Verbs (Overview)",
        "Adjectives as Nouns", "Be used to / Get used to", "Articles / Silent Letters",
        "Concrete and Abstract Nouns", "Wish + Modal Verbs", "Future Continuous", "Future Perfect",
        "Future in the Past", "Ellipsis", "Substitution", "Reduced Infinitives / Verbs with Compliments",
        "Informal Discourse Markers", "Have / Get something done", "Collective Nouns",
        "Either........ or/ Neither .......nor", "So / Such", "Generic 'The'"
    ],
    "Kids": [
        "Introducing yourself", "Alphabet + Numbers + Countries", "Ages and Nationalities + to be",
        "Possessive Adjectives", "Plural nouns", "This/These (What is this? this is...) + (colors)",
        "That/Those", "Expressing preference (What's your favorite...?)",
        "Who is this/that? + What do you do?", "Have/ Have got", "Simple Present (To Be) - Affirmative",
        "Simple Present (To Be) - Negative", "Simple Present (To Be) - Interrogative", "Feelings",
        "Simple Present (Other Verbs) - Affirmative", "Simple Present (Other Verbs) - Negative",
        "Simple Present (Other Verbs) - Interrogative", "Which?", "There is/are",
        "Where? - Prepositions of Place, Position", "How many (also using there are)", "Modals: can/can’t",
        "Some / a", "Likes and dislikes - Short answer do/don't", "Gerunds - verb + ing: like/hate/love",
        "PRESENT CONTINUOUS", "Present Continuous (Yes/No)", "Would and Want (also include some and any)",
        "Possessive Apostrophe - Possessives – use of ‘s, s’", "Possessive Pronouns (also using whose)",
        "What's The Time?", "When?", "Days and Prepositions/Frequency Phrases"
    ]
}

# --- TEXTOS DA INTERFACE (Tradução) ---
UI_TEXT = {
    "PT": {
        "title": "🇬🇧 Gerador de Quiz de Inglês",
        "sidebar_config": "Configurações",
        "lbl_level": "Selecione o Nível",
        "lbl_topic": "Selecione o Tópico",
        "lbl_questions": "Quantidade de Questões",
        "btn_generate": "Buscar / Gerar",
        "btn_new": "➕ Novas Perguntas",
        "msg_generating": "Gerando {} perguntas inéditas para o nível '{}'...",
        "msg_success": "Quiz carregado com sucesso!",
        "msg_error": "Falha ao gerar o quiz.",
        "header_results": "📊 Resultados",
        "btn_submit": "Corrigir Quiz",
        "expander_hint": "💡 Precisa de uma dica?",
        "feedback_title": "🤖 Feedback do Professor",
        "feedback_loading": "O Professor está corrigindo seu exercício...",
        "prompt_hint": "Write the hint in Portuguese (PT-BR).",
        "prompt_analysis": "Dê feedback em Português (PT-BR)."
    },
    "EN": {
        "title": "🇬🇧 English Quiz Generator",
        "sidebar_config": "Settings",
        "lbl_level": "Select Level",
        "lbl_topic": "Select Topic",
        "lbl_questions": "Number of Questions",
        "btn_generate": "Search / Generate",
        "btn_new": "➕ New Questions",
        "msg_generating": "Generating {} new questions for '{}' level...",
        "msg_success": "Quiz loaded successfully!",
        "msg_error": "Failed to generate quiz.",
        "header_results": "📊 Results",
        "btn_submit": "Submit Answers",
        "expander_hint": "💡 Need a hint?",
        "feedback_title": "🤖 Teacher's Feedback",
        "feedback_loading": "Teacher is grading your exercise...",
        "prompt_hint": "Write the hint in English, keep it simple.",
        "prompt_analysis": "Give feedback in English."
    }
}

# Validação de Segurança
if not API_KEY:
    st.error("❌ ERRO: API Key não encontrada. Verifique seu arquivo .env")
    st.stop()

client = genai.Client(api_key=API_KEY)

# --- FUNÇÕES DE BANCO DE DADOS ---
def init_db():
    if IS_CLOUD and not os.path.exists("/data"):
        os.makedirs("/data", exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabela de Tópicos
    c.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            level TEXT,
            created_at TIMESTAMP,
            UNIQUE(topic, level)
        )
    ''')
    
    # Tabela de Questões
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            question_text TEXT,
            options TEXT,
            correct_answer TEXT,
            hint TEXT,
            FOREIGN KEY(quiz_id) REFERENCES quizzes(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_existing_questions_text(topic, level):
    """Retorna lista de textos de perguntas já existentes para este tópico+nível."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT q.question_text 
        FROM questions q
        JOIN quizzes z ON q.quiz_id = z.id 
        WHERE z.topic = ? AND z.level = ?
    ''', (topic, level))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_quiz_from_db(topic, level, num_questions):
    """Tenta recuperar perguntas do cache."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM quizzes WHERE topic = ? AND level = ?", (topic, level))
    quiz_row = c.fetchone()
    
    questions_data = []
    if quiz_row:
        quiz_id = quiz_row[0]
        c.execute("SELECT question_text, options, correct_answer, hint FROM questions WHERE quiz_id = ? ORDER BY RANDOM() LIMIT ?", (quiz_id, num_questions))
        rows = c.fetchall()
        for row in rows:
            questions_data.append({
                "question": row[0],
                "options": json.loads(row[1]),
                "answer": row[2],
                "hint": row[3] if row[3] else ""
            })
        conn.close()
        
        # Se tiver menos do que o pedido, retorna o que tem + None para sinalizar que precisa gerar mais
        if len(questions_data) < num_questions:
            return None, questions_data
        return questions_data, []
    
    conn.close()
    return None, []

def save_quiz_to_db(topic, level, questions):
    """Salva novas perguntas no banco."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO quizzes (topic, level, created_at) VALUES (?, ?, ?)", (topic, level, datetime.now()))
        c.execute("SELECT id FROM quizzes WHERE topic = ? AND level = ?", (topic, level))
        quiz_id = c.fetchone()[0]
        
        for q in questions:
            # Evita duplicatas exatas
            c.execute("SELECT id FROM questions WHERE quiz_id = ? AND question_text = ?", (quiz_id, q['question']))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO questions (quiz_id, question_text, options, correct_answer, hint)
                    VALUES (?, ?, ?, ?, ?)
                ''', (quiz_id, q['question'], json.dumps(q['options']), q['answer'], q.get('hint', '')))
        conn.commit()
    except Exception as e:
        st.error(f"Erro de Banco de Dados: {e}")
    finally:
        conn.close()

# --- INTEGRAÇÃO COM GEMMA (IA) ---
def generate_quiz_with_gemma(topic, level, num_questions, lang_code, existing_questions=[]):
    """Gera o quiz com instruções gramaticais rígidas."""
    
    hint_instruction = UI_TEXT[lang_code]["prompt_hint"]
    
    # 1. Filtro de Duplicidade (Injeta contexto negativo)
    forbidden_context = ""
    if existing_questions:
        subset = existing_questions[-15:] # Limita para não estourar tokens
        forbidden_list = "\n".join([f"- {q}" for q in subset])
        forbidden_context = f"DO NOT generate questions similar to these:\n{forbidden_list}\n"

    # 2. Contexto de Audiência (Nível)
    audience_context = ""
    if level == "Kids":
        audience_context = "Target audience: CHILDREN (Kids). Use playful themes (animals, colors, toys, school) but keep the grammar strict."
    else:
        audience_context = f"Target audience: {level} level students. Ensure vocabulary and sentence complexity match this CEFR level."

    # 3. Instrução Gramatical Rígida (A "Vacina" contra Simple Present genérico)
    grammar_instruction = f"""
    CRITICAL GRAMMAR INSTRUCTION:
    The questions must SPECIFICALLY test the grammar rule or vocabulary defined in the topic: "{topic}".
    
    - If the topic is "Past Continuous", ALL sentences must use "was/were + verb-ing".
    - If the topic is "Present Perfect", ALL sentences must use "have/has + past participle".
    - If the topic is "Future with Going To", ALL sentences must use "going to".
    - Do NOT default to "Simple Present" unless the topic explicitly asks for it.
    - Ensure the distractors (wrong options) are plausible mistakes for this specific level.
    """

    prompt = f"""
    You are an expert ESL/EFL English Teacher. Create a multiple-choice quiz.
    
    Topic: '{topic}'
    Level: {level}
    {audience_context}
    
    {grammar_instruction}
    
    Generate exactly {num_questions} NEW questions.
    The Questions and Options MUST be in English.
    
    {forbidden_context}
    
    STRICT JSON OUTPUT INSTRUCTIONS:
    - Return ONLY a raw JSON list.
    - Do NOT include markdown formatting (like ```json).
    - Do NOT include introduction text.
    
    JSON Schema:
    [
        {{
            "question": "The sentence with a gap or a question",
            "options": ["Correct Option", "Distractor 1", "Distractor 2", "Distractor 3"],
            "answer": "Correct Option",
            "hint": "{hint_instruction} Explain the specific grammar rule found in this question. Don't give the answer."
        }}
    ]
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.6) # Temp baixa para precisão gramatical
        )
        
        # Limpeza manual do JSON (Gemma 3 Workaround)
        txt = response.text.strip()
        if txt.startswith("```json"): txt = txt.replace("```json", "", 1)
        if txt.startswith("```"): txt = txt.replace("```", "", 1)
        if txt.endswith("```"): txt = txt.rsplit("```", 1)[0]
        
        return json.loads(txt.strip())
    except Exception as e:
        st.error(f"Erro na API: {e}")
        return []

def analyze_performance(score, total, topic, level, mistakes, lang_code):
    """Gera feedback pedagógico."""
    instr = UI_TEXT[lang_code]["prompt_analysis"]
    mistakes_txt = "\n".join([f"Q: {m['q']} | User: {m['user']} | Correct: {m['correct']}" for m in mistakes])
    
    prompt = f"""
    Act as a friendly English teacher providing feedback to a {level} student.
    Topic: {topic}. Score: {score}/{total}.
    
    Mistakes made:
    {mistakes_txt}
    
    {instr}
    Structure the response:
    1. Brief encouraging comment.
    2. Explanation of the errors (simple and direct).
    3. A specific study tip for this topic.
    """
    try:
        return client.models.generate_content_stream(model=MODEL_ID, contents=prompt)
    except:
        return "Não foi possível gerar a análise."

# --- INTERFACE PRINCIPAL (STREAMLIT) ---
def main():
    st.set_page_config(page_title="English Quiz Generator", layout="wide")
    init_db()

    # --- SIDEBAR ---
    with st.sidebar:
        # Seletor de Idioma
        lang = st.radio("Language / Idioma", ["PT", "EN"], horizontal=True)
        t = UI_TEXT[lang] # Carrega textos traduzidos
        
        st.markdown("---")
        st.header(t["sidebar_config"])
        
        # 1. Nível
        level = st.selectbox(t["lbl_level"], list(COURSE_SYLLABUS.keys()))
        
        # 2. Tópico (Filtra baseado no Nível)
        available_topics = COURSE_SYLLABUS[level]
        topic = st.selectbox(t["lbl_topic"], available_topics)
        
        # 3. Slider (5 a 20)
        num_questions = st.slider(t["lbl_questions"], 5, 20, 5)
        
        col1, col2 = st.columns(2)
        btn_gen = col1.button(t["btn_generate"])
        btn_new = col2.button(t["btn_new"])

        # Lógica de Geração
        if btn_gen or btn_new:
            # Reseta estado
            st.session_state['user_answers'] = {}
            st.session_state['submitted'] = False
            st.session_state['analysis_done'] = False
            
            with st.spinner("..."):
                # Busca do Banco
                db_quiz, existing_pool = get_quiz_from_db(topic, level, num_questions)
                
                # Decide se chama a IA (Botão 'Novas' OU Banco Vazio/Incompleto)
                if btn_new or db_quiz is None:
                    exist_txts = get_existing_questions_text(topic, level)
                    
                    # Calcula quantas faltam
                    needed = num_questions if btn_new else (num_questions - len(existing_pool))
                    if needed < 1: needed = 1
                    
                    st.info(t["msg_generating"].format(needed, level))
                    
                    # Chama IA
                    new_q = generate_quiz_with_gemma(topic, level, needed, lang, exist_txts)
                    
                    if new_q:
                        save_quiz_to_db(topic, level, new_q)
                        final, _ = get_quiz_from_db(topic, level, num_questions)
                        st.session_state['quiz_data'] = final
                    else:
                        st.error(t["msg_error"])
                else:
                    st.success(t["msg_success"])
                    st.session_state['quiz_data'] = db_quiz

    # --- ÁREA DE CONTEÚDO ---
    st.title(t["title"])
    
    if 'quiz_data' in st.session_state and st.session_state['quiz_data']:
        quiz = st.session_state['quiz_data']
        
        with st.form("quiz_form"):
            st.caption(f"📚 {level} > {topic}")
            
            for i, q in enumerate(quiz):
                st.markdown(f"#### {i+1}. {q['question']}")
                
                # Dica Oculta
                if q.get('hint'):
                    with st.expander(t["expander_hint"]):
                        st.info(q['hint'])
                
                # Opções
                st.session_state['user_answers'][i] = st.radio(
                    "Options", 
                    q['options'], 
                    key=f"q_{i}", 
                    index=None, 
                    label_visibility="collapsed"
                )
                st.markdown("---")
            
            if st.form_submit_button(t["btn_submit"]):
                st.session_state['submitted'] = True

    # --- CORREÇÃO E ANÁLISE ---
    if st.session_state.get('submitted') and not st.session_state.get('analysis_done'):
        score = 0
        mistakes = []
        quiz = st.session_state['quiz_data']
        
        st.header(t["header_results"])
        
        for i, q in enumerate(quiz):
            u = st.session_state['user_answers'].get(i)
            if u == q['answer']:
                score += 1
                st.markdown(f"**Q{i+1}:** :green[{u}] (Correct)")
            else:
                mistakes.append({"q":q['question'], "user":u, "correct":q['answer']})
                st.markdown(f"**Q{i+1}:** :red[{u}] (Correct: {q['answer']})")
        
        st.subheader(f"Score: {score}/{len(quiz)}")
        st.markdown("---")
        
        # Feedback IA
        st.subheader(t["feedback_title"])
        box = st.empty()
        full = ""
        
        with st.spinner(t["feedback_loading"]):
            stream = analyze_performance(score, len(quiz), topic, level, mistakes, lang)
            
            if isinstance(stream, str):
                box.write(stream)
            else:
                for chunk in stream:
                    if chunk.text:
                        full += chunk.text
                        box.markdown(full + "▌")
                box.markdown(full)
        
        st.session_state['analysis_done'] = True

if __name__ == "__main__":
    main()
    
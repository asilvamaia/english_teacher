import streamlit as st
import sqlite3
import json
import os
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# --- CONFIGURAÇÕES ---
# Tenta pegar a chave do .env (local) ou dos segredos do Streamlit (cloud)
API_KEY = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
MODEL_ID = "gemma-3-27b-it"

# Verifica se está rodando em ambiente de nuvem (Fly/Railway) para persistência
IS_CLOUD = os.path.exists("/data")
DB_FILE = "/data/english_quiz.db" if IS_CLOUD else "english_quiz.db"

# --- DICIONÁRIO DE TEXTOS (INTERFACE BILÍNGUE) ---
UI_TEXT = {
    "PT": {
        "title": "🇬🇧 Gerador de Quiz de Inglês",
        "sidebar_config": "Configurações",
        "lbl_topic": "Tópico Gramatical ou Vocabulário",
        "lbl_questions": "Quantidade de Questões",
        "btn_generate": "Buscar / Gerar",
        "btn_new": "➕ Novas Perguntas",
        "msg_generating": "Gerando {} perguntas inéditas com IA...",
        "msg_success": "Quiz carregado com sucesso!",
        "msg_error": "Falha ao gerar o quiz. Tente novamente.",
        "header_results": "📊 Resultados",
        "btn_submit": "Corrigir Quiz",
        "expander_hint": "💡 Precisa de uma dica?",
        "no_hint": "Sem dica disponível.",
        "feedback_title": "🤖 Feedback do Professor",
        "feedback_loading": "Analisando seu desempenho...",
        "score_label": "Sua Nota",
        "prompt_hint_instruction": "Write the hint in Portuguese (PT-BR).",
        "prompt_analysis_instruction": "Dê feedback em Português (PT-BR).",
        "placeholder_topic": "Ex: Past Perfect, Travel Vocabulary"
    },
    "EN": {
        "title": "🇬🇧 English Quiz Generator",
        "sidebar_config": "Settings",
        "lbl_topic": "Grammar Topic or Vocabulary",
        "lbl_questions": "Number of Questions",
        "btn_generate": "Search / Generate",
        "btn_new": "➕ New Questions",
        "msg_generating": "Generating {} new questions with AI...",
        "msg_success": "Quiz loaded successfully!",
        "msg_error": "Failed to generate quiz.",
        "header_results": "📊 Results",
        "btn_submit": "Submit Answers",
        "expander_hint": "💡 Need a hint?",
        "no_hint": "No hint available.",
        "feedback_title": "🤖 Teacher's Feedback",
        "feedback_loading": "Analyzing your performance...",
        "score_label": "Your Score",
        "prompt_hint_instruction": "Write the hint in English, but keep it simple.",
        "prompt_analysis_instruction": "Give feedback in English.",
        "placeholder_topic": "E.g., Past Perfect, Travel Vocabulary"
    }
}

# Validação da Chave de API
if not API_KEY:
    st.error("❌ ERRO: API Key não encontrada. Configure GOOGLE_API_KEY no arquivo .env")
    st.stop()

# Inicializa o cliente Google GenAI
client = genai.Client(api_key=API_KEY)

# --- BANCO DE DADOS (SQLite) ---
def init_db():
    """Inicializa o banco e cria tabelas se necessário."""
    # Cria diretório de dados se estiver na nuvem
    if IS_CLOUD and not os.path.exists("/data"):
        os.makedirs("/data", exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabela de Tópicos
    c.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT UNIQUE,
            created_at TIMESTAMP
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
    
    # Migration: Adiciona coluna 'hint' se o banco for antigo
    try:
        c.execute("ALTER TABLE questions ADD COLUMN hint TEXT")
    except sqlite3.OperationalError:
        pass # Coluna já existe
        
    conn.commit()
    conn.close()

def get_existing_questions_text(topic):
    """Busca textos das perguntas existentes para evitar duplicatas."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT q.question_text 
        FROM questions q
        JOIN quizzes z ON q.quiz_id = z.id 
        WHERE z.topic = ?
    ''', (topic.lower().strip(),))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_quiz_from_db(topic, num_questions):
    """Recupera um quiz do banco de dados (Cache)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM quizzes WHERE topic = ?", (topic.lower().strip(),))
    quiz_row = c.fetchone()
    
    questions_data = []
    if quiz_row:
        quiz_id = quiz_row[0]
        # Pega perguntas aleatórias do tópico
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
        
        # Se tiver menos perguntas do que o solicitado, retorna o que tem mas avisa que faltam
        if len(questions_data) < num_questions:
            return None, questions_data
        return questions_data, []
    
    conn.close()
    return None, []

def save_quiz_to_db(topic, questions):
    """Salva novas perguntas no banco."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        # Garante que o tópico existe
        c.execute("INSERT OR IGNORE INTO quizzes (topic, created_at) VALUES (?, ?)", (topic.lower().strip(), datetime.now()))
        c.execute("SELECT id FROM quizzes WHERE topic = ?", (topic.lower().strip(),))
        quiz_id = c.fetchone()[0]
        
        for q in questions:
            # Verifica se a pergunta exata já existe neste quiz
            c.execute("SELECT id FROM questions WHERE quiz_id = ? AND question_text = ?", (quiz_id, q['question']))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO questions (quiz_id, question_text, options, correct_answer, hint)
                    VALUES (?, ?, ?, ?, ?)
                ''', (quiz_id, q['question'], json.dumps(q['options']), q['answer'], q.get('hint', '')))
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao salvar no banco: {e}")
    finally:
        conn.close()

# --- INTEGRAÇÃO COM GEMMA (GOOGLE API) ---
def generate_quiz_with_gemma(topic, num_questions, lang_code, existing_questions_list=[]):
    """Gera o quiz. Removemos o response_mime_type pois o Gemma 3 ainda não suporta."""
    
    # Instrução de idioma para a Dica
    hint_instruction = UI_TEXT[lang_code]["prompt_hint_instruction"]

    # Contexto para evitar repetição
    forbidden_context = ""
    if existing_questions_list:
        forbidden_list = "\n".join([f"- {q}" for q in existing_questions_list])
        forbidden_context = f"DO NOT generate questions similar to these ones, I already have them:\n{forbidden_list}\n"

    prompt = f"""
    You are an expert English Teacher. Create a multiple-choice quiz about: '{topic}'.
    Generate exactly {num_questions} NEW questions.
    
    The Questions and Options MUST be in English.
    
    {forbidden_context}
    
    STRICT FORMATTING INSTRUCTIONS:
    - Return ONLY a raw JSON list.
    - Do NOT include markdown formatting (like ```json).
    - Do NOT include introduction text.
    
    JSON Schema:
    [
        {{
            "question": "Question text in English",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Option A",
            "hint": "A subtle explanation about the grammar rule. Do NOT reveal the answer directly. {hint_instruction}"
        }}
    ]
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7 # Criatividade moderada
            )
        )
        
        # --- CORREÇÃO: LIMPEZA MANUAL DO JSON ---
        content = response.text.strip()
        
        # Remove blocos de código Markdown se o modelo adicionar
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
        if content.startswith("```"):
            content = content.replace("```", "", 1)
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
            
        return json.loads(content.strip())
        
    except json.JSONDecodeError:
        st.error("Erro na formatação JSON do modelo. Tente novamente.")
        return []
    except Exception as e:
        st.error(f"Erro na API do Google: {e}")
        return []

def analyze_performance(score, total, topic, mistakes, lang_code):
    """Gera feedback pedagógico."""
    analysis_instruction = UI_TEXT[lang_code]["prompt_analysis_instruction"]
    
    mistakes_text = "\n".join([f"- Q: {m['q']}\n  User: {m['user']}\n  Correct: {m['correct']}" for m in mistakes])
    
    prompt = f"""
    Act as a friendly English teacher. The student took a quiz on '{topic}'.
    Score: {score}/{total}.
    Mistakes:
    {mistakes_text}
    
    {analysis_instruction}
    Provide:
    1. A short comment on the score.
    2. Explanation of the mistakes.
    3. A study tip.
    """
    
    try:
        # Retorna um gerador (stream)
        return client.models.generate_content_stream(model=MODEL_ID, contents=prompt)
    except Exception as e:
        return f"Erro ao gerar feedback: {e}"

# --- APP STREAMLIT ---
def main():
    st.set_page_config(page_title="Gemma English Tutor", layout="wide")
    init_db()

    # --- SIDEBAR: CONFIGURAÇÕES ---
    with st.sidebar:
        # Seletor de Idioma
        lang = st.radio("Language / Idioma", ["PT", "EN"], index=0, horizontal=True)
        t = UI_TEXT[lang] # Carrega os textos do idioma escolhido
        
        st.markdown("---")
        st.header(t["sidebar_config"])
        
        topic = st.text_input(t["lbl_topic"], value="Present Perfect", placeholder=t["placeholder_topic"])
        num_questions = st.slider(t["lbl_questions"], 3, 10, 5)
        
        col1, col2 = st.columns(2)
        generate_btn = col1.button(t["btn_generate"])
        force_new_btn = col2.button(t["btn_new"])

        # Lógica de Botões (Gerar/Buscar)
        if generate_btn or force_new_btn:
            # Limpa estados anteriores
            st.session_state['user_answers'] = {}
            st.session_state['submitted'] = False
            st.session_state['analysis_done'] = False
            
            with st.spinner("..."):
                # 1. Tenta buscar do banco
                db_quiz, existing_pool = get_quiz_from_db(topic, num_questions)
                
                # 2. Se for forçado novas OU banco vazio/insuficiente
                if force_new_btn or db_quiz is None:
                    existing_texts = get_existing_questions_text(topic)
                    
                    # Calcula quantas faltam gerar
                    needed = num_questions if force_new_btn else (num_questions - len(existing_pool))
                    if needed < 1: needed = 1
                    
                    st.info(t["msg_generating"].format(needed))
                    
                    # Chama o Gemma com a correção de JSON
                    new_questions = generate_quiz_with_gemma(topic, needed, lang, existing_texts)
                    
                    if new_questions:
                        save_quiz_to_db(topic, new_questions)
                        # Recarrega do banco para garantir mistura
                        final_quiz, _ = get_quiz_from_db(topic, num_questions)
                        st.session_state['quiz_data'] = final_quiz
                    else:
                        st.error(t["msg_error"])
                else:
                    st.success(t["msg_success"])
                    st.session_state['quiz_data'] = db_quiz

    # --- ÁREA PRINCIPAL ---
    st.title(t["title"])
    
    if 'quiz_data' in st.session_state and st.session_state['quiz_data']:
        quiz = st.session_state['quiz_data']
        
        with st.form("quiz_form"):
            st.subheader(f"Topic: {topic}")
            
            for idx, q in enumerate(quiz):
                st.markdown(f"#### {idx + 1}. {q['question']}")
                
                # Exibe a dica dentro de um expander
                if q.get('hint'):
                    with st.expander(t["expander_hint"]):
                        st.info(q['hint'])
                
                # Opções
                st.session_state['user_answers'][idx] = st.radio(
                    "Options", 
                    q['options'], 
                    key=f"q_{idx}", 
                    index=None, # Nenhum selecionado por padrão
                    label_visibility="collapsed"
                )
                st.markdown("---")
            
            # Botão de Envio
            if st.form_submit_button(t["btn_submit"]):
                st.session_state['submitted'] = True

    # --- RESULTADOS E ANÁLISE ---
    if st.session_state.get('submitted') and not st.session_state.get('analysis_done'):
        score = 0
        mistakes = []
        quiz = st.session_state['quiz_data']
        
        st.header(t["header_results"])
        
        # Correção Visual
        for idx, q in enumerate(quiz):
            u_ans = st.session_state['user_answers'].get(idx)
            
            if u_ans == q['answer']:
                score += 1
                st.markdown(f"**Q{idx+1}:** :green[{u_ans}] (Correct)")
            else:
                mistakes.append({"q": q['question'], "user": u_ans, "correct": q['answer']})
                st.markdown(f"**Q{idx+1}:** :red[{u_ans}] (Correct: {q['answer']})")

        st.subheader(f"{t['score_label']}: {score}/{len(quiz)}")
        st.markdown("---")
        
        # Feedback com IA
        st.subheader(t["feedback_title"])
        res_box = st.empty()
        full_text = ""
        
        with st.spinner(t["feedback_loading"]):
            stream = analyze_performance(score, len(quiz), topic, mistakes, lang)
            
            # Tratamento do Stream
            if isinstance(stream, str):
                res_box.write(stream)
            else:
                for chunk in stream:
                    # Verifica se o chunk tem texto (segurança)
                    if chunk.text:
                        full_text += chunk.text
                        res_box.markdown(full_text + "▌")
                res_box.markdown(full_text)
        
        st.session_state['analysis_done'] = True

if __name__ == "__main__":
    main()
    
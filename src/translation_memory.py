"""
Translation Memory - Sistema di memoria delle traduzioni per consistenza e performance
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import os


class TranslationMemory:
    """Gestisce la memoria delle traduzioni per garantire consistenza e velocità"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inizializza la Translation Memory
        
        Args:
            db_path: Path del database SQLite (default: ~/.translate-idml/tm.db)
        """
        if db_path is None:
            # Crea directory default se non esiste
            default_dir = Path.home() / '.translate-idml'
            default_dir.mkdir(exist_ok=True)
            db_path = str(default_dir / 'tm.db')
            
        self.db_path = db_path
        self.conn = None
        self._init_database()
        
    def _init_database(self):
        """Inizializza il database SQLite con le tabelle necessarie"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Crea tabelle
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_text TEXT NOT NULL,
                source_lang TEXT,
                target_text TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                context_hash TEXT,
                document_type TEXT,
                glossary_version TEXT,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 1,
                confidence REAL DEFAULT 1.0,
                UNIQUE(source_text, target_lang, context_hash)
            );
            
            CREATE INDEX IF NOT EXISTS idx_source_text ON translations(source_text);
            CREATE INDEX IF NOT EXISTS idx_context ON translations(context_hash);
            CREATE INDEX IF NOT EXISTS idx_langs ON translations(source_lang, target_lang);
            
            CREATE TABLE IF NOT EXISTS terminology (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL,
                language TEXT NOT NULL,
                translation TEXT NOT NULL,
                target_language TEXT NOT NULL,
                domain TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(term, language, target_language, domain)
            );
            
            CREATE INDEX IF NOT EXISTS idx_term ON terminology(term);
            CREATE INDEX IF NOT EXISTS idx_term_langs ON terminology(language, target_language);
            
            CREATE TABLE IF NOT EXISTS consistency_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                replacement TEXT NOT NULL,
                language TEXT NOT NULL,
                rule_type TEXT NOT NULL, -- 'punctuation', 'capitalization', 'formatting'
                description TEXT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
        
    def add_translation(self, source_text: str, target_text: str, target_lang: str,
                       source_lang: Optional[str] = None, context: Optional[str] = None,
                       document_type: Optional[str] = None, glossary_version: Optional[str] = None,
                       model: Optional[str] = None) -> int:
        """
        Aggiunge una traduzione alla memoria
        
        Args:
            source_text: Testo originale
            target_text: Testo tradotto
            target_lang: Lingua di destinazione
            source_lang: Lingua di origine
            context: Contesto della traduzione
            document_type: Tipo di documento
            glossary_version: Versione del glossario usato
            model: Modello di traduzione usato
            
        Returns:
            ID della traduzione inserita
        """
        context_hash = self._compute_context_hash(context, document_type, target_lang)
        
        try:
            cursor = self.conn.execute("""
                INSERT INTO translations 
                (source_text, source_lang, target_text, target_lang, context_hash, 
                 document_type, glossary_version, model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_text, target_lang, context_hash) 
                DO UPDATE SET
                    target_text = excluded.target_text,
                    last_used = CURRENT_TIMESTAMP,
                    usage_count = usage_count + 1
            """, (source_text, source_lang, target_text, target_lang, context_hash,
                  document_type, glossary_version, model))
            
            self.conn.commit()
            return cursor.lastrowid
            
        except sqlite3.Error as e:
            print(f"Errore nell'aggiunta alla TM: {e}")
            return -1
            
    def get_exact_match(self, source_text: str, target_lang: str,
                       context: Optional[str] = None, 
                       document_type: Optional[str] = None) -> Optional[Dict]:
        """
        Cerca una corrispondenza esatta nella memoria
        
        Args:
            source_text: Testo da cercare
            target_lang: Lingua di destinazione
            context: Contesto della traduzione
            document_type: Tipo di documento
            
        Returns:
            Dizionario con la traduzione trovata o None
        """
        context_hash = self._compute_context_hash(context, document_type, target_lang)
        
        cursor = self.conn.execute("""
            SELECT * FROM translations
            WHERE source_text = ? AND target_lang = ? AND context_hash = ?
            ORDER BY last_used DESC
            LIMIT 1
        """, (source_text, target_lang, context_hash))
        
        row = cursor.fetchone()
        if row:
            # Aggiorna timestamp di utilizzo
            self.conn.execute("""
                UPDATE translations 
                SET last_used = CURRENT_TIMESTAMP, usage_count = usage_count + 1
                WHERE id = ?
            """, (row['id'],))
            self.conn.commit()
            
            return dict(row)
        return None
        
    def get_fuzzy_matches(self, source_text: str, target_lang: str,
                         threshold: float = 0.8, max_results: int = 5) -> List[Dict]:
        """
        Cerca corrispondenze fuzzy (simili) nella memoria
        
        Args:
            source_text: Testo da cercare
            target_lang: Lingua di destinazione
            threshold: Soglia di similarità (0-1)
            max_results: Numero massimo di risultati
            
        Returns:
            Lista di dizionari con le traduzioni trovate e il punteggio di similarità
        """
        # Ottieni candidati con la stessa lingua target
        cursor = self.conn.execute("""
            SELECT * FROM translations
            WHERE target_lang = ?
            ORDER BY usage_count DESC
            LIMIT 1000
        """, (target_lang,))
        
        candidates = []
        for row in cursor:
            similarity = SequenceMatcher(None, source_text.lower(), 
                                       row['source_text'].lower()).ratio()
            if similarity >= threshold:
                result = dict(row)
                result['similarity'] = similarity
                candidates.append(result)
                
        # Ordina per similarità e prendi i migliori
        candidates.sort(key=lambda x: x['similarity'], reverse=True)
        return candidates[:max_results]
        
    def add_terminology(self, term: str, translation: str, 
                       source_lang: str, target_lang: str,
                       domain: Optional[str] = None, notes: Optional[str] = None) -> int:
        """
        Aggiunge un termine al database terminologico
        
        Args:
            term: Termine originale
            translation: Traduzione del termine
            source_lang: Lingua del termine
            target_lang: Lingua della traduzione
            domain: Dominio/contesto del termine
            notes: Note aggiuntive
            
        Returns:
            ID del termine inserito
        """
        try:
            cursor = self.conn.execute("""
                INSERT INTO terminology 
                (term, language, translation, target_language, domain, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(term, language, target_language, domain) 
                DO UPDATE SET translation = excluded.translation, notes = excluded.notes
            """, (term, source_lang, translation, target_lang, domain, notes))
            
            self.conn.commit()
            return cursor.lastrowid
            
        except sqlite3.Error as e:
            print(f"Errore nell'aggiunta terminologia: {e}")
            return -1
            
    def get_terminology(self, terms: List[str], source_lang: str, 
                       target_lang: str, domain: Optional[str] = None) -> Dict[str, str]:
        """
        Ottiene le traduzioni per una lista di termini
        
        Args:
            terms: Lista di termini da cercare
            source_lang: Lingua dei termini
            target_lang: Lingua delle traduzioni
            domain: Dominio specifico (opzionale)
            
        Returns:
            Dizionario termine -> traduzione
        """
        terminology = {}
        
        for term in terms:
            query = """
                SELECT translation FROM terminology
                WHERE term = ? AND language = ? AND target_language = ?
            """
            params = [term, source_lang, target_lang]
            
            if domain:
                query += " AND domain = ?"
                params.append(domain)
                
            cursor = self.conn.execute(query, params)
            row = cursor.fetchone()
            
            if row:
                terminology[term] = row['translation']
                
        return terminology
        
    def add_consistency_rule(self, pattern: str, replacement: str, 
                           language: str, rule_type: str, 
                           description: Optional[str] = None) -> int:
        """
        Aggiunge una regola di consistenza
        
        Args:
            pattern: Pattern da cercare (regex)
            replacement: Sostituzione da applicare
            language: Lingua a cui si applica
            rule_type: Tipo di regola
            description: Descrizione della regola
            
        Returns:
            ID della regola inserita
        """
        cursor = self.conn.execute("""
            INSERT INTO consistency_rules 
            (pattern, replacement, language, rule_type, description)
            VALUES (?, ?, ?, ?, ?)
        """, (pattern, replacement, language, rule_type, description))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def get_consistency_rules(self, language: str, 
                            rule_type: Optional[str] = None) -> List[Dict]:
        """
        Ottiene le regole di consistenza per una lingua
        
        Args:
            language: Lingua delle regole
            rule_type: Tipo specifico di regole (opzionale)
            
        Returns:
            Lista di regole applicabili
        """
        query = "SELECT * FROM consistency_rules WHERE language = ? AND active = 1"
        params = [language]
        
        if rule_type:
            query += " AND rule_type = ?"
            params.append(rule_type)
            
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor]
        
    def _compute_context_hash(self, context: Optional[str], 
                            document_type: Optional[str], 
                            target_lang: Optional[str] = None) -> str:
        """
        Calcola un hash del contesto per raggruppare traduzioni simili
        CRITICAL: Include target_lang per evitare contaminazione tra lingue
        
        Args:
            context: Contesto testuale
            document_type: Tipo di documento  
            target_lang: Lingua target (ESSENZIALE per cache separato)
            
        Returns:
            Hash del contesto inclusa la lingua target
        """
        # CRITICO: Includi lingua target per separare cache per lingua
        context_str = f"{context or ''}{document_type or ''}{target_lang or ''}"
        return hashlib.md5(context_str.encode()).hexdigest()[:8]
        
    def export_tmx(self, output_path: str, source_lang: str, 
                  target_lang: str, min_usage: int = 1):
        """
        Esporta la memoria in formato TMX (Translation Memory eXchange)
        
        Args:
            output_path: Path del file TMX da creare
            source_lang: Lingua sorgente
            target_lang: Lingua target
            min_usage: Utilizzo minimo per l'export
        """
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Crea struttura TMX
        tmx = Element('tmx', version='1.4')
        header = SubElement(tmx, 'header', {
            'creationtool': 'translate-idml',
            'creationtoolversion': '1.0',
            'datatype': 'plaintext',
            'segtype': 'sentence',
            'adminlang': 'en',
            'srclang': source_lang,
            'o-tmf': 'translate-idml'
        })
        
        body = SubElement(tmx, 'body')
        
        # Esporta traduzioni
        cursor = self.conn.execute("""
            SELECT DISTINCT source_text, target_text, created_at
            FROM translations
            WHERE source_lang = ? AND target_lang = ? AND usage_count >= ?
            ORDER BY usage_count DESC
        """, (source_lang, target_lang, min_usage))
        
        for row in cursor:
            tu = SubElement(body, 'tu', {
                'creationdate': row['created_at'].replace(' ', 'T') + 'Z'
            })
            
            # Segmento sorgente
            tuv_src = SubElement(tu, 'tuv', {'xml:lang': source_lang})
            seg_src = SubElement(tuv_src, 'seg')
            seg_src.text = row['source_text']
            
            # Segmento target
            tuv_tgt = SubElement(tu, 'tuv', {'xml:lang': target_lang})
            seg_tgt = SubElement(tuv_tgt, 'seg')
            seg_tgt.text = row['target_text']
            
        # Formatta e salva
        rough_string = tostring(tmx, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(reparsed.toprettyxml(indent='  '))
            
    def get_statistics(self) -> Dict:
        """
        Ottiene statistiche sulla memoria di traduzione
        
        Returns:
            Dizionario con statistiche
        """
        stats = {}
        
        # Conteggi base
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM translations")
        stats['total_translations'] = cursor.fetchone()['count']
        
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM terminology")
        stats['total_terms'] = cursor.fetchone()['count']
        
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM consistency_rules WHERE active = 1")
        stats['active_rules'] = cursor.fetchone()['count']
        
        # Lingue più usate
        cursor = self.conn.execute("""
            SELECT target_lang, COUNT(*) as count 
            FROM translations 
            GROUP BY target_lang 
            ORDER BY count DESC 
            LIMIT 5
        """)
        stats['top_languages'] = [(row['target_lang'], row['count']) for row in cursor]
        
        # Traduzioni più riutilizzate
        cursor = self.conn.execute("""
            SELECT source_text, target_text, usage_count 
            FROM translations 
            ORDER BY usage_count DESC 
            LIMIT 10
        """)
        stats['most_used'] = [dict(row) for row in cursor]
        
        return stats
        
    def close(self):
        """Chiude la connessione al database"""
        if self.conn:
            self.conn.close()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
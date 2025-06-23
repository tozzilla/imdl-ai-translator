# Translate IDML

Un'applicazione Python per tradurre automaticamente il contenuto testuale di file InDesign IDML usando l'API di OpenAI, mantenendo intatto il layout e la formattazione originale.

## 🚀 Caratteristiche

- **Traduzione automatica**: Utilizza modelli OpenAI (GPT-3.5, GPT-4) per traduzioni di alta qualità
- **Preservazione layout**: Mantiene intatta la formattazione e la struttura del documento InDesign
- **Supporto multilingue**: Oltre 40 lingue supportate
- **Estrazione intelligente**: Identifica automaticamente il testo traducibile escludendo codici e ID
- **Gestione batch**: Ottimizza le chiamate API raggruppando i testi
- **Stima costi**: Calcola i costi stimati prima della traduzione
- **CLI intuitiva**: Interfaccia da riga di comando semplice e potente

## 📋 Requisiti

- Python 3.8+
- Chiave API OpenAI
- File IDML di InDesign

## 🔧 Installazione

1. **Clona il repository**:
```bash
git clone <repository-url>
cd translate-imdl
```

2. **Crea ambiente virtuale** (raccomandato):
```bash
python3 -m venv venv
source venv/bin/activate  # Su macOS/Linux
# oppure venv\Scripts\activate su Windows
```

3. **Installa le dipendenze**:
```bash
pip install -r requirements.txt
```

4. **Configura l'API OpenAI**:
```bash
cp .env.example .env
# Modifica .env inserendo la tua chiave API OpenAI
```

## 🎯 Utilizzo

**Nota**: Ricordati di attivare l'ambiente virtuale prima dell'uso:
```bash
source venv/bin/activate  # Su macOS/Linux
```

### Comando base
```bash
python src/main.py translate documento.idml --target-lang it
```

### Esempi d'uso

**Traduzione semplice (inglese → italiano)**:
```bash
python src/main.py translate brochure.idml -t it -o brochure_italiano.idml
```

**Con lingua di origine specificata**:
```bash
python src/main.py translate document.idml -s en -t es --model gpt-4
```

**Con contesto per migliorare la traduzione**:
```bash
python src/main.py translate marketing.idml -t fr --context "Marketing brochure for luxury products"
```

**Anteprima senza tradurre**:
```bash
python src/main.py translate documento.idml -t de --preview
```

**Stima costi**:
```bash
python src/main.py translate documento.idml -t ja --estimate-cost
```

### Altri comandi utili

**Elenco lingue supportate**:
```bash
python src/main.py languages
```

**Informazioni su un file IDML**:
```bash
python src/main.py info documento.idml
```

## 🌍 Lingue Supportate

L'applicazione supporta oltre 40 lingue, tra cui:

- **Europee**: English (en), Italiano (it), Español (es), Français (fr), Deutsch (de), Nederlands (nl), Svenska (sv), ecc.
- **Asiatiche**: 中文 (zh), 日本語 (ja), 한국어 (ko), ไทย (th), Tiếng Việt (vi), ecc.
- **Altre**: العربية (ar), עברית (he), Русский (ru), Polski (pl), ecc.

Usa il comando `python src/main.py languages` per l'elenco completo.

## ⚙️ Configurazione

### Variabili d'ambiente (.env)
```bash
# Richiesta
OPENAI_API_KEY=your_openai_api_key_here

# Opzionali
OPENAI_MODEL=gpt-3.5-turbo
LOG_LEVEL=INFO
TEMP_DIR=./temp
AUTO_BACKUP=true
```

### Modelli supportati
- `gpt-3.5-turbo` (default, economico)
- `gpt-4` (qualità superiore, più costoso)
- `gpt-4-turbo-preview` (bilanciato)

## 📊 Gestione Costi

L'applicazione include funzionalità per stimare e monitorare i costi:

```bash
# Stima costo prima della traduzione
python src/main.py translate documento.idml -t it --estimate-cost

# Output verboso mostra sempre la stima
python src/main.py translate documento.idml -t it --verbose
```

### Costi indicativi (USD)
- **GPT-3.5-turbo**: ~$0.002 per 1K token
- **GPT-4**: ~$0.06 per 1K token  
- **Documento tipico** (1000 parole): $0.10-0.50

## 🔍 Come Funziona

1. **Apertura IDML**: Il file viene decompresso e analizzato
2. **Estrazione testo**: Identifica il contenuto traducibile nelle "stories"
3. **Filtraggio intelligente**: Esclude codici, ID, URL e contenuti non testuali
4. **Traduzione batch**: Raggruppa i testi per chiamate API ottimizzate
5. **Reinserimento**: Sostituisce il testo tradotto mantenendo la formattazione
6. **Ricostruzione**: Genera il nuovo file IDML tradotto

## 🧪 Test

Esegui i test unitari:
```bash
pytest tests/
```

Con coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## 📁 Struttura Progetto

```
translate-imdl/
├── src/
│   ├── idml_processor.py    # Gestione file IDML
│   ├── text_extractor.py    # Estrazione testo
│   ├── translator.py        # Interfaccia OpenAI
│   └── main.py             # CLI principale
├── tests/                  # Test unitari
├── config/
│   └── settings.py         # Configurazioni
├── requirements.txt        # Dipendenze
└── .env.example           # Template variabili ambiente
```

## 🔧 Sviluppo

### Setup ambiente di sviluppo
```bash
# Installa dipendenze development
pip install -r requirements.txt

# Esegui test
pytest

# Lint del codice
flake8 src/
```

### Architettura
- **IDMLProcessor**: Gestisce apertura/salvataggio file IDML
- **TextExtractor**: Estrae e filtra testo traducibile
- **Translator**: Interfaccia con OpenAI API
- **CLI**: Interfaccia utente da riga di comando

## 🚨 Limitazioni

- Richiede file IDML (non supporta .indd nativi)
- Mantiene la struttura ma potrebbe richiedere aggiustamenti manuali per lingue con lunghezze molto diverse
- Dipende dalla disponibilità dell'API OpenAI
- Non traduce testo incorporato in immagini

## 🤝 Contribuire

1. Fork del repository
2. Crea un branch per la feature (`git checkout -b feature/nome-feature`)
3. Commit delle modifiche (`git commit -am 'Aggiunge nuova feature'`)
4. Push del branch (`git push origin feature/nome-feature`)
5. Apri una Pull Request

## 📝 Licenza

[Specifica la licenza qui]

## 🆘 Supporto

Per problemi o domande:
1. Controlla la documentazione
2. Cerca negli issue esistenti
3. Apri un nuovo issue con dettagli del problema

## 📈 Roadmap

- [ ] Support per file .indd nativi
- [ ] Interfaccia web
- [ ] Traduzione batch di cartelle
- [ ] Integrazione con altri servizi di traduzione
- [ ] Plugin InDesign diretto
- [ ] Gestione memoria traduzione (TM)

---

*Sviluppato per semplificare il workflow di localizzazione di documenti InDesign* 🎨
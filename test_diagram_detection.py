#!/usr/bin/env python3
"""
Test script per il rilevamento automatico di diagrammi
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from overflow_detector import OverflowDetector, TextFrameMetrics
from overflow_manager import OverflowManager
import json

def create_test_frame_metrics():
    """Crea metriche di test per diversi tipi di frame"""
    
    # Frame 1: Diagramma tipico con parole chiave
    diagram_frame = TextFrameMetrics(
        frame_id="diagram_frame_1",
        width=300.0,
        height=250.0,
        x=100.0,
        y=100.0,
        column_count=1,
        column_gutter=12.0,
        inset_spacing=(3.0, 3.0, 3.0, 3.0),
        font_size=9.0,
        leading=10.8,
        char_count=150,  # Relativamente poco testo per l'area
        estimated_overflow_risk=1.4
    )
    
    # Frame 2: Testo normale (non diagramma)
    text_frame = TextFrameMetrics(
        frame_id="text_frame_1",
        width=400.0,
        height=600.0,
        x=50.0,
        y=50.0,
        column_count=1,
        column_gutter=12.0,
        inset_spacing=(6.0, 6.0, 6.0, 6.0),
        font_size=12.0,
        leading=14.4,
        char_count=800,  # Molto testo
        estimated_overflow_risk=0.8
    )
    
    # Frame 3: Diagramma complesso (critico)
    complex_diagram = TextFrameMetrics(
        frame_id="complex_diagram_1",
        width=200.0,
        height=180.0,
        x=200.0,
        y=200.0,
        column_count=1,
        column_gutter=12.0,
        inset_spacing=(2.0, 2.0, 2.0, 2.0),
        font_size=8.0,
        leading=9.6,
        char_count=250,  # Molto testo in spazio piccolo
        estimated_overflow_risk=1.6
    )
    
    return {
        "diagram_frame_1": diagram_frame,
        "text_frame_1": text_frame,
        "complex_diagram_1": complex_diagram
    }

def create_test_stories_data():
    """Crea dati di test per le stories con contenuto tipico di diagrammi"""
    
    from xml.etree import ElementTree as ET
    
    # Story 1: Contenuto diagramma con parole chiave
    story1_content = """
    <Story>
        <ParagraphStyleRange>
            <CharacterStyleRange>
                <Content>Überprüfung der Komponenten</Content>
                <Content>Funktionalitätsprüfung durchführen</Content>
                <Content>Ja → weiter zu Schritt 2</Content>
                <Content>Nein → Inspektion wiederholen</Content>
                <Content>Dokumentation verfügbar?</Content>
            </CharacterStyleRange>
        </ParagraphStyleRange>
    </Story>
    """
    
    # Story 2: Contenuto testo normale
    story2_content = """
    <Story>
        <ParagraphStyleRange>
            <CharacterStyleRange>
                <Content>Questo è un testo normale che spiega le procedure di installazione del sistema SafeGuard. Il manuale contiene informazioni dettagliate sui requisiti tecnici e le specifiche di montaggio.</Content>
            </CharacterStyleRange>
        </ParagraphStyleRange>
    </Story>
    """
    
    # Story 3: Contenuto diagramma complesso
    story3_content = """
    <Story>
        <ParagraphStyleRange>
            <CharacterStyleRange>
                <Content>Sichtprüfung Bauteile</Content>
                <Content>Beschädigte Komponenten?</Content>
                <Content>Verformung erkennbar?</Content>
                <Content>Korrosion vorhanden?</Content>
                <Content>Effizienz der beweglichen Teile</Content>
                <Content>System funktionsfähig?</Content>
                <Content>Neue Zertifizierung erforderlich</Content>
            </CharacterStyleRange>
        </ParagraphStyleRange>
    </Story>
    """
    
    return {
        "Story_1": {"root": ET.fromstring(story1_content)},
        "Story_2": {"root": ET.fromstring(story2_content)},
        "Story_3": {"root": ET.fromstring(story3_content)}
    }

def test_diagram_detection():
    """Test principale per il rilevamento diagrammi"""
    
    print("🔍 Test Rilevamento Automatico Diagrammi")
    print("=" * 50)
    
    # Inizializza detector
    detector = OverflowDetector()
    manager = OverflowManager()
    
    # Crea dati di test
    frame_metrics = create_test_frame_metrics()
    stories_data = create_test_stories_data()
    
    print(f"\n📊 Frame di test creati: {len(frame_metrics)}")
    for frame_id, metrics in frame_metrics.items():
        print(f"  - {frame_id}: {metrics.width}x{metrics.height}, "
              f"{metrics.char_count} char, risk: {metrics.estimated_overflow_risk}")
    
    # Esegui rilevamento diagrammi
    print("\n🎯 Esecuzione rilevamento diagrammi...")
    diagram_frames = detector.detect_diagram_frames(frame_metrics, stories_data)
    
    print(f"\n📈 Diagrammi rilevati: {len(diagram_frames)}")
    
    # Mostra risultati dettagliati
    for frame_id, diagram_info in diagram_frames.items():
        print(f"\n🔍 Frame: {frame_id}")
        print(f"  📊 Punteggio diagramma: {diagram_info['diagram_score']:.3f}")
        print(f"  🎯 Priorità compressione: {diagram_info['compression_priority']}")
        print(f"  ⚠️  Fattori di rischio:")
        for risk in diagram_info['risk_factors']:
            print(f"    - {risk}")
        print(f"  💡 Strategie raccomandate:")
        for strategy in diagram_info['recommended_strategies']:
            print(f"    - {strategy}")
    
    # Genera report di rilevamento
    print("\n📋 Generazione report rilevamento...")
    detection_report = detector.generate_diagram_detection_report(diagram_frames)
    
    print(f"\n📊 Report Rilevamento Diagrammi:")
    print(f"  - Totale diagrammi: {detection_report['summary']['total_diagrams']}")
    print(f"  - Punteggio medio: {detection_report['summary']['average_diagram_score']}")
    print(f"  - Distribuzione priorità: {detection_report['summary']['priority_distribution']}")
    print(f"  - Frame critici: {detection_report['summary']['critical_frames_count']}")
    
    print(f"\n💡 Raccomandazioni:")
    for rec in detection_report['recommendations']:
        print(f"  - {rec}")
    
    print(f"\n📋 Prossimi passi:")
    for step in detection_report['next_steps']:
        print(f"  - {step}")
    
    # Test compressione specifica per diagrammi
    print(f"\n🔧 Test compressione diagrammi...")
    
    test_texts = [
        "Überprüfung der Komponenten durchführen - ist die Funktionalität gewährleistet?",
        "Sichtprüfung der beschädigten Komponenten und Dokumentation verfügbar machen",
        "Wenn Korrosion vorhanden, dann Ersetzen und neue Zertifizierung durchführen"
    ]
    
    for i, text in enumerate(test_texts):
        frame_id = f"diagram_frame_{i+1}"
        if frame_id in diagram_frames:
            strategies = diagram_frames[frame_id]['recommended_strategies']
            compressed = manager.apply_diagram_specific_compression(text, strategies)
            
            print(f"\n  📝 Testo {i+1}:")
            print(f"    Originale ({len(text)} char): {text}")
            print(f"    Compresso ({len(compressed)} char): {compressed}")
            print(f"    Risparmio: {len(text) - len(compressed)} caratteri "
                  f"({((len(text) - len(compressed)) / len(text) * 100):.1f}%)")
    
    # Salva report dettagliato
    report_file = "diagram_detection_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        # Converti oggetti non serializzabili
        serializable_report = {
            'detection_report': detection_report,
            'frame_analysis': {
                frame_id: {
                    'diagram_score': info['diagram_score'],
                    'compression_priority': info['compression_priority'],
                    'risk_factors': info['risk_factors'],
                    'recommended_strategies': info['recommended_strategies']
                }
                for frame_id, info in diagram_frames.items()
            }
        }
        json.dump(serializable_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Report dettagliato salvato in: {report_file}")
    
    return diagram_frames, detection_report

if __name__ == "__main__":
    try:
        diagram_frames, report = test_diagram_detection()
        
        print(f"\n✅ Test completato con successo!")
        print(f"📊 Rilevati {len(diagram_frames)} frame diagramma")
        print(f"🎯 {report['summary']['critical_frames_count']} frame critici identificati")
        
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
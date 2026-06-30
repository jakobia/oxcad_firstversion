# OXCAD - Open CAD Application

En öppen CAD-applikation för 3D-modellering och design, byggd med Python, PySide6 och CadQuery.

## Om projektet

OXCAD är en parametrisk CAD-applikation som gör det möjligt att skapa och modifiera 3D-geometrier genom ett intuitivt grafiskt gränssnitt. Programmet använder **CadQuery** för kraftfull geometrimodellering och **VTK** för avancerad 3D-visualisering.

### Funktioner

- **3D-visningsport** - Interaktiv 3D-rendering av geometriska modeller
- **Skissverktyg** - Rita och skapa 2D-skisser
- **Geometrikälla** - Generera primitiva former som kuber, cylindrar och andra objekt
- **Mörkt tema** - Ergonomiskt mörkare användargränssnitt
- **Modularstruktur** - Välorganiserad kodstruktur för enkel underhållning och utökning

## Systemkrav

- Python 3.8 eller senare
- Windows/macOS/Linux
- GPU rekommenderas för bättre 3D-prestanda (VTK)

## Installation

### 1. Klona eller ladda ned projektet

```bash
cd c:\oxcad_firstversion
```

### 2. Skapa en virtuell miljö (rekommenderat)

```bash
python -m venv .venv
```

### 3. Aktivera den virtuella miljön

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 4. Installera beroenden

```bash
pip install -r requirements.txt
```

Du kan även använda installationsskriptet:
```bash
install.bat  # Windows
```

## Starta applikationen

### Metod 1: Använd run.bat (Windows)
```bash
run.bat
```

### Metod 2: Kör direkt med Python
```bash
python cadapp/main.py
```

### Metod 3: Kontrollera Qt3D-installation (optional)
```bash
python check_qt3d.py
```

## Projektstruktur

```
oxcad_firstversion/
├── cadapp/
│   ├── main.py                 # Ingångspunkt för applikationen
│   ├── core/
│   │   ├── geometry_engine.py  # Geometrimotor baserad på CadQuery
│   │   └── operations.py        # Geometriska operationer
│   ├── gui/
│   │   ├── main_window.py       # Huvudfönster och menystruktur
│   │   ├── viewport_3d.py       # 3D-visningsport (VTK)
│   │   ├── sketch_canvas.py     # 2D-skissverktyg
│   │   └── toolbar.py           # Verktygslist
│   ├── utils/
│   │   └── logger.py            # Loggningskonfiguration
│   └── data/
│       └── icons/               # Ikoner och resurser
├── requirements.txt             # Pythonberoenden
├── install.bat                  # Installationsskript (Windows)
├── run.bat                       # Startskript (Windows)
├── check_qt3d.py                # Qt3D-kontroll
└── README.md                    # Denna fil
```

## Huvudberoenden

| Paket | Version | Syfte |
|-------|---------|-------|
| **PySide6** | 6.11.1 | GUI-ramverk |
| **CadQuery** | 2.8.0 | Parametrisk modellering |
| **VTK** | 9.6.2 | 3D-visualisering |
| **NumPy** | 2.4.6 | Numeriska beräkningar |
| **SciPy** | 1.18.0 | Vetenskaplig beräkning |
| **Matplotlib** | 3.11.0 | Visualisering |

Fullständig lista finns i [requirements.txt](requirements.txt).

## Användning

### Starta applikationen

1. Kör `run.bat` eller `python cadapp/main.py`
2. Huvudfönstret öppnas med en mörk tema
3. Använd verktygslisten för att skapa geometrier
4. Interagera med 3D-vyn för att rottera, zooma och panorera

### Skapa en enkel form

1. Gå till **Geometri** > **Primitiver** i menyn
2. Välj en form (t.ex. Kub)
3. Ange dimensioner i dialogrutan
4. Modellen visas i 3D-vyn

## Utveckling

### Struktur för nya funktioner

- **Nya geometriska operationer**: Lägg till i `cadapp/core/operations.py`
- **GUI-komponenter**: Skapa nya klasser i `cadapp/gui/`
- **Logik**: Utöka `cadapp/core/geometry_engine.py`

### Tillägg av nya verktyg

1. Skapa en ny åtgärd i `cadapp/gui/toolbar.py`
2. Koppla den till motsvarande geometrioperation i `cadapp/core/`
3. Uppdatera menyn i `cadapp/gui/main_window.py`

## Felsökning

### Applikationen startar inte
- Kontrollera att alla beroenden är installerade: `pip install -r requirements.txt`
- Verifiera Python-version: `python --version` (bör vara 3.8+)

### 3D-vyn är svart/tom
- Uppdatera grafikdrivrutiner
- Testa med `check_qt3d.py` för diagnostik
- Kontrollera VTK-installation: `pip install --upgrade vtk`

### ImportError för CadQuery
- Se till att den virtuella miljön är aktiverad
- Installera om: `pip install --force-reinstall cadquery`

## Framtidsplaner

- [ ] Mera avancerade skissverktyg
- [ ] Stöd för import/export av CAD-format (STEP, IGES, STL)
- [ ] Modelhistorik och undo/redo
- [ ] Animationer och rendering-alternativ
- [ ] Plugin-system för utökning

## Licens

Projektet är under utveckling. Licens kommer att definieras senare.

## Kontakt & Bidrag

För frågor, rapportera fel eller bidra till utvecklingen - se projektrepositoryiet.

---

**Status**: 🚀 Tidigt utvecklingsstadium (v0.1)  
**Senast uppdaterad**: 2026-06-30

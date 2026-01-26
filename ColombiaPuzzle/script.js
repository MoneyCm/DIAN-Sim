// Data: Departments and Animals
// We map the GeoJSON 'name' property to our animal data.
const ANIMAL_DATA = {
    "Amazonas": "Delfín Rosado",
    "Antioquia": "Oso de Anteojos",
    "Arauca": "Chigüiro",
    "Atlántico": "Tití Cabeziblanco",
    "Bolívar": "Manatí del Caribe",
    "Boyacá": "Venado de Cola Blanca",
    "Caldas": "Cóndor de los Andes",
    "Caquetá": "Guacamaya",
    "Casanare": "Oso Palmero",
    "Cauca": "Cóndor",
    "Cesar": "Iguana",
    "Chocó": "Rana Dorada",
    "Córdoba": "Sinú Parakeet",
    "Cundinamarca": "Oso de Anteojos",
    "Guainía": "Tonina",
    "Guaviare": "Jaguar",
    "Huila": "Caballito de Mar (Fósil)",
    "La Guajira": "Flamenco Rosado",
    "Magdalena": "Caimán Aguja",
    "Meta": "Caimán Llanero",
    "Nariño": "Oso de Anteojos",
    "Norte de Santander": "Oso Andino",
    "Putumayo": "Danta",
    "Quindío": "Palma de Cera (Flora)",
    "Risaralda": "Tangara",
    "San Andrés y Providencia": "Cangrejo Negro",
    "Santander": "Hormiga Culona",
    "Sucre": "Tiburón",
    "Tolima": "Puma",
    "Valle del Cauca": "Gallito de Roca",
    "Vaupés": "Tucán",
    "Vichada": "Danta"
};

const MAP_URL = "https://gist.githubusercontent.com/john-guerra/43c7656821069d00dcbc/raw/colombia.geo.json";

document.addEventListener("DOMContentLoaded", () => {
    initGame();
});

async function initGame() {
    const mapWrapper = document.getElementById('colombia-map-wrapper');
    const piecesList = document.getElementById('pieces-list');

    // 1. Fetch Map Data
    try {
        const response = await fetch(MAP_URL);
        const geojson = await response.json();

        // 2. Setup D3 Projection
        const width = mapWrapper.clientWidth || 800;
        const height = mapWrapper.clientHeight || 600;

        const projection = d3.geoMercator();

        // Auto-fit projection to features
        // Note: For Highcharts GeoJSON, we might need to be explicit if fitSize fails due to crs.
        // But usually fitSize works if GeoJSON is standard. 
        // Let's try specifying standard fitExtent with padding.
        projection.fitExtent([[20, 20], [width - 20, height - 20]], geojson);

        const pathGenerator = d3.geoPath().projection(projection);

        // 3. Create SVG
        const svg = d3.select("#colombia-map-wrapper")
            .append("svg")
            .attr("width", "100%")
            .attr("height", "100%")
            .attr("viewBox", `0 0 ${width} ${height}`);

        // 4. Render Targets (The Map)
        svg.selectAll("path")
            .data(geojson.features)
            .enter()
            .append("path")
            .attr("d", pathGenerator)
            .attr("class", "department-outline")
            .attr("id", d => `target-${normalizeName(d.properties["NOMBRE_DPT"])}`)
            .attr("data-name", d => normalizeName(d.properties["NOMBRE_DPT"]))
            .on("dragover", (e) => e.preventDefault()) // Allow drop
            .on("drop", handleDrop)
            .on("dragenter", function () { d3.select(this).classed("hovered", true); })
            .on("dragleave", function () { d3.select(this).classed("hovered", false); });

        // 5. Create Pieces
        geojson.features.forEach(feature => {
            // John Guerra's GeoJSON uses 'NOMBRE_DPT' (e.g. "ANTIOQUIA")
            const rawName = feature.properties["NOMBRE_DPT"];
            if (!rawName) return;

            // Normalize to Title Case to match our ANIMAL_DATA keys (e.g. "Antioquia")
            // Special handling for Bogota which might be "SANTAFE DE BOGOTA D.C" or similar
            const name = normalizeName(rawName);

            createPiece(name, piecesList, feature, pathGenerator);

            // Fix Map Target Visibility for San Andres
            if (name === "San Andrés y Providencia") {
                const target = document.getElementById(`target-${name}`);
                if (target) {
                    // Move it to visible area (inset) and scale it up
                    // This is a hacky transform based on standard projection coords
                    // Assuming map is roughly 500x600. 
                    // San Andres is top left.
                    target.style.transformBox = "fill-box";
                    target.style.transformOrigin = "center";
                    target.style.transform = "scale(5) translate(20px, 20px)";
                    target.style.strokeWidth = "0.2px"; // Compensate scaling
                }
            }
        });

    } catch (err) {
        console.error("Error loading map:", err);
        mapWrapper.innerHTML = "<p>Error cargando el mapa real. Verifica tu conexión.</p>";
    }
}

function toTitleCase(str) {
    return str.replace(
        /\w\S*/g,
        text => text.charAt(0).toUpperCase() + text.substring(1).toLowerCase()
    );
}

function createPiece(name, container, feature, pathGenerator) {
    const animal = ANIMAL_DATA[name] || "Fauna Nativa";

    // Create Piece Element
    const div = document.createElement("div");
    div.className = "puzzle-piece";
    div.draggable = true;
    div.setAttribute("data-name", name);
    div.addEventListener("dragstart", handleDragStart);
    // Add click event to show info immediately
    div.addEventListener("click", () => showInfo(name));

    // ... (SVG creation code omitted for brevity, keeping as is) ...

    // Correct logic for icon generation 
    const svgNS = "http://www.w3.org/2000/svg";
    const pieceSvg = document.createElementNS(svgNS, "svg");
    pieceSvg.setAttribute("width", "80");
    pieceSvg.setAttribute("height", "80");
    pieceSvg.setAttribute("viewBox", `${x - 10} ${y - 10} ${dx + 20} ${dy + 20}`);

    const path = document.createElementNS(svgNS, "path");
    path.setAttribute("d", pathGenerator(feature));
    path.setAttribute("fill", getRandomColor());
    path.setAttribute("stroke", "#fff");

    // Special visibility fix for San Andres in the PIECE icon
    if (name.includes("San Andres") || name.includes("Archipielago")) {
        // Force a simplified viewbox or scale for the icon
        // Actually, let's just make the stroke thicker and maybe zoom the viewBox
        // But simply relying on auto-viewbox above (x, y, dx, dy) should handle it if dx/dy are small!
        // The issue is likely the map target is small. Elements in the list should be OK if bounds are correct.
    }

    pieceSvg.appendChild(path);
    div.appendChild(pieceSvg);

    const label = document.createElement("div");
    label.innerText = name.replace("Archipielago De ", ""); // Shorten visuals
    label.style.fontSize = "10px";
    label.style.textAlign = "center";
    div.appendChild(label);

    container.appendChild(div);
}

// Helper to normalize specific department names to match our Animal Data keys
function normalizeName(rawName) {
    let name = toTitleCase(rawName);
    // Fix San Andres
    if (name.includes("San Andres")) {
        return "San Andrés y Providencia";
    }
    // Fix Bogota
    if (name.includes("Bogota")) {
        return "Cundinamarca"; // Or separate if we have data. Usually Bogota is inside Cundinamarca in simple maps.
    }
    return name;
}

// COLORS
function getRandomColor() {
    const colors = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#e67e22"];
    return colors[Math.floor(Math.random() * colors.length)];
}

// DRAG & DROP
let draggedName = null;

function handleDragStart(e) {
    draggedName = e.target.getAttribute("data-name");
    // Identify explicitly
    e.dataTransfer.setData("text/plain", draggedName);
}

function handleDrop(e) {
    e.preventDefault();
    // e.target might be the path.
    // D3 events pass (event, datum). But we used native .on()? 
    // D3 v7 .on("event", (event, d) => ...)

    // Use the native event target to find the group/path
    // But since we are inside D3 context, let's keep it simple.

    // We need to find the "data-name" of the drop target.
    // It might be deeply nested if user drops on a label? No, target is <path>.

    const targetName = e.target.getAttribute("data-name");

    if (draggedName && targetName && draggedName === targetName) {
        // Correct!
        e.target.classList.add("solved");
        e.target.style.fill = "#2ecc71"; // Success color

        // Find piece and remove
        const piece = document.querySelector(`.puzzle-piece[data-name="${CSS.escape(draggedName)}"]`);
        if (piece) piece.remove();

        updateScore();
        showInfo(draggedName);
    }
}

function updateScore() {
    const s = document.getElementById("score");
    s.innerText = parseInt(s.innerText) + 1;
}

function showInfo(name) {
    const info = document.getElementById("info-box");
    info.classList.remove("hidden");
    document.getElementById("info-title").innerText = name;
    document.getElementById("info-animal").innerText = `Fauna: ${ANIMAL_DATA[name] || 'Desconocida'}`;
}

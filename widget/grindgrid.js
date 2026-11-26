// grindgrid — Scriptable widget.
// Widget parameter: "<base_url>[;theme]", e.g. "http://192.0.2.10:8080;intensity"
// Themes: binary (default), intensity, sports. Colours mirror grindgrid/web.py.

const EMPTY = "#9aa4b140"
const BINARY = "#2fbf71"
const SHADES = ["#26c1654d", "#26c16585", "#26c165bb", "#26c165"]
const SPORT_COLORS = { run: "#ff6b3d", ride: "#3d8bff", strength: "#a35cff",
                       swim: "#16c1c8", walk: "#7cc35a", other: "#e5b52b" }
const WEEKS = { small: 10, medium: 20, large: 26, extraLarge: 53 }

const [base, themeArg] = (args.widgetParameter || "").split(";").map(s => s.trim())
const theme = ["binary", "intensity", "sports"].includes(themeArg) ? themeArg : "binary"
const family = config.widgetFamily || "medium"

const fm = FileManager.local()
const cachePath = fm.joinPath(fm.documentsDirectory(), "grindgrid-cache.json")

function color(hex) {
  const a = hex.length === 9 ? parseInt(hex.slice(7), 16) / 255 : 1
  return new Color(hex.slice(0, 7), a)
}

function dayColor(d) {
  if (d.future) return null
  if (d.level === 0) return EMPTY
  if (theme === "intensity") return SHADES[d.level - 1]
  if (theme === "sports") return SPORT_COLORS[d.sport_group]
  return BINARY
}

async function loadDays() {
  if (!base) throw new Error("no server")
  const req = new Request(base.replace(/\/$/, "") + "/api/days")
  req.timeoutInterval = 10
  const data = await req.loadJSON()
  fm.writeString(cachePath, JSON.stringify(data))
  return { days: data.days, offline: false }
}

function cachedDays() {
  if (!fm.fileExists(cachePath)) return null
  return { days: JSON.parse(fm.readString(cachePath)).days, offline: true }
}

function drawGrid(days, width, height) {
  const weeks = Math.ceil(days.length / 7)
  const step = Math.min(width / weeks, height / 7)
  const gap = Math.max(1.5, step * 0.18)
  const ctx = new DrawContext()
  ctx.size = new Size(weeks * step, 7 * step)
  ctx.opaque = false
  ctx.respectScreenScale = true
  days.forEach((d, i) => {
    const c = dayColor(d)
    if (!c) return
    const p = new Path()
    p.addRoundedRect(new Rect(Math.floor(i / 7) * step, (i % 7) * step, step - gap, step - gap), 2, 2)
    ctx.addPath(p)
    ctx.setFillColor(color(c))
    ctx.fillPath()
  })
  return ctx.getImage()
}

async function build() {
  const w = new ListWidget()
  w.setPadding(12, 12, 12, 12)
  let result
  try { result = await loadDays() } catch (e) { result = cachedDays() }
  if (!result) {
    w.addText("grindgrid: no data").font = Font.mediumSystemFont(13)
    return w
  }
  if (family.startsWith("accessory")) {
    // lock screen: too small and monochrome for a grid, show the last 4 weeks as text
    const n = result.days.filter(d => !d.future).slice(-28).filter(d => d.level > 0).length
    w.addText(`${n}/28 dni`).font = Font.semiboldSystemFont(14)
    return w
  }
  const days = result.days.slice(-(WEEKS[family] || WEEKS.medium) * 7)
  const head = w.addStack()
  const title = head.addText("grindgrid")
  title.font = Font.semiboldSystemFont(12)
  head.addSpacer()
  const active = days.filter(d => d.level > 0).length
  const info = head.addText(result.offline ? `offline · ${active} dni` : `${active} dni`)
  info.font = Font.systemFont(11)
  info.textOpacity = 0.6
  w.addSpacer(6)
  const sizes = { small: [134, 100], medium: [300, 110], large: [300, 280], extraLarge: [660, 280] }
  const [gw, gh] = sizes[family] || sizes.medium
  const img = w.addImage(drawGrid(days, gw, gh))
  img.centerAlignImage()
  w.addSpacer()
  w.refreshAfterDate = new Date(Date.now() + 30 * 60 * 1000)
  return w
}

const widget = await build()
if (config.runsInWidget) Script.setWidget(widget)
else await widget.presentMedium()
Script.complete()

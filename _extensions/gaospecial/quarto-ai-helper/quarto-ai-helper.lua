-- quarto-ai-helper.lua
-- Inject the AI helper CSS and JavaScript into HTML output.
-- The JS automatically detects error output blocks and adds "Ask AI" buttons.

local function readFile(path)
  local file = io.open(path, "r")
  if not file then return nil end
  local content = file:read("*a")
  file:close()
  return content
end

function Meta(meta)
  -- Only inject for HTML format
  if not quarto.doc.is_format("html") then
    return meta
  end

  -- Read the CSS file and inject into <head>
  local cssPath = quarto.utils.resolve_path("quarto-ai-helper.css")
  local cssContent = readFile(cssPath)
  if cssContent then
    quarto.doc.include_text("in-header", "<style>\n" .. cssContent .. "\n</style>")
  end

  -- Read the JS file and inject at the end of <body>
  local jsPath = quarto.utils.resolve_path("quarto-ai-helper.js")
  local jsContent = readFile(jsPath)
  if jsContent then
    quarto.doc.include_text("after-body", "<script>\n" .. jsContent .. "\n</script>")
  end

  return meta
end

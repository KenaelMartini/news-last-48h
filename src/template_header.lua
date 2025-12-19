function Header(el)
  -- On ignore les headers Markdown, Pandoc gère le vrai en-tête
  return {}
end

function Meta(m)
  return pandoc.RawBlock('openxml',
  [[
  <w:sectPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:headerReference w:type="default" r:id="rId999"/>
  </w:sectPr>
  ]])
end

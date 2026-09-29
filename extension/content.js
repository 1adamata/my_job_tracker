(() => {
  if (globalThis.__JOB_QUEUE_CAPTURE__) return;
  globalThis.__JOB_QUEUE_CAPTURE__ = true;
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "EXTRACT_PAGE") return false;
    try { sendResponse({ok: true, page: extractPage()}); }
    catch (error) { sendResponse({ok: false, error: error.message}); }
    return false;
  });

  function extractPage() {
    const structured = extractStructured();
    const root = chooseRoot();
    const clone = root.cloneNode(true);
    clone.querySelectorAll("script,style,noscript,svg,canvas,iframe,nav,footer,header,form,button,input,select,textarea,[role='navigation'],[aria-hidden='true']").forEach(node => node.remove());
    const text = clean(clone.innerText || clone.textContent || "").slice(0, 120000);
    const meta = Object.fromEntries([...document.querySelectorAll("meta[name],meta[property]")].map(node => [node.name || node.getAttribute("property"), node.content]).filter(([key,value]) => key && value).slice(0,80));
    return {url: location.href, title: document.title, language: document.documentElement.lang || null, capturedAt: new Date().toISOString(), headings: [...root.querySelectorAll("h1,h2,h3")].map(x => clean(x.innerText)).filter(Boolean).slice(0,40), meta, structured, text};
  }
  function chooseRoot() {
    const selectors = ["[itemtype*='JobPosting']","main","article","[role='main']",".job-description","#job-description",".description"];
    const candidates = selectors.flatMap(selector => [...document.querySelectorAll(selector)]);
    return candidates.sort((a,b) => (b.innerText?.length || 0) - (a.innerText?.length || 0))[0] || document.body;
  }
  function extractStructured() {
    for (const script of document.querySelectorAll("script[type='application/ld+json']")) {
      try {
        const parsed = JSON.parse(script.textContent); const nodes = Array.isArray(parsed) ? parsed : parsed["@graph"] || [parsed];
        const p = nodes.find(node => node?.["@type"] === "JobPosting");
        if (p) return {title:p.title||null,hiringOrganization:p.hiringOrganization?.name||null,datePosted:p.datePosted||null,validThrough:p.validThrough||null,employmentType:p.employmentType||null,jobLocationType:p.jobLocationType||null,baseSalary:p.baseSalary||null,applicantLocationRequirements:p.applicantLocationRequirements||null};
      } catch (_) {}
    }
    return null;
  }
  function clean(value="") { return value.replace(/\u00a0/g," ").replace(/[ \t]+/g," ").replace(/\n{3,}/g,"\n\n").trim(); }
})();

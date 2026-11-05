; Namespaced managed-job entrypoint. Loaded only for an explicit opted-in request.
procedure(cadexJobTarget(lib cell view writable)
  let((cv win kind opened)
    unless(ddGetObj(lib cell view) error("Existing target not found: %s/%s/%s" lib cell view))
    cv=dbFindOpenCellViewByName(lib cell view)
    when(cv win=geGetEditCellViewWindow(cv))
    unless(win
      opened=t
      kind=if(view=="layout" then "maskLayout" else "schematic")
      win=deOpenCellView(lib cell view kind nil if(writable then "a" else "r"))
    )
    unless(win error("Cannot open named view; check write locks"))
    cv=geGetEditCellView(win)
    unless(cv && cv~>libName==lib && cv~>cellName==cell && cv~>viewName==view error("Target identity mismatch"))
    when(writable && !member(cv~>mode list("a" "w")) error("Target is read-only; no lock override permitted"))
    list(cv win opened)
  )
)
procedure(cadexRequire(condition message)
  unless(condition error("%s" message))
  t
)
procedure(cadexReport(data) cadexResult=data)
procedure(cadexCheck()
  let((counts)
    unless(cadexCV~>viewName=="schematic" error("Use the project's layout verification flow"))
    unless(envGetVal("schematic" "updateConn") && envGetVal("schematic" "runSRC")
      error("Connectivity extraction and schematic rules must be enabled; settings were not changed"))
    counts=schCheck(cadexCV)
    unless(listp(counts) && length(counts)>=2 && numberp(car(counts)) && numberp(cadr(counts))
      error("Invalid schematic-check result"))
    counts
  )
)
procedure(cadexExpectConnection(instance1 terminal1 instance2 terminal2)
  cadexExpectations=cons(list("connection" instance1 terminal1 instance2 terminal2) cadexExpectations)
)
procedure(cadexExpectNet(instance terminal netName)
  cadexExpectations=cons(list("net" instance terminal netName) cadexExpectations)
)
procedure(cadexJobAssertConnections()
  let((first second)
    foreach(item cadexExpectations
      first=cadexInstTerm(cadr(item) caddr(item))~>net
      unless(first error("Expected terminal is disconnected"))
      if(car(item)=="connection" then
        second=cadexInstTerm(cadddr(item) nth(4 item))~>net
        unless(first==second error("Requested terminal connection failed after checking"))
      else
        unless(first~>name==cadddr(item) error("Requested net identity failed after checking"))
      )
    )
    t
  )
)
procedure(cadexJobRun(token lib cell view path runDir save allowExisting inspection)
  let((identity target cadexCV cadexWindow cadexRunDir cadexResult cadexExpectations dirty baseline finalCounts outcome saved)
    identity=cadexLiveIdentity()
    unless(identity && cadr(identity)==token error("Session identity changed"))
    target=cadexJobTarget(lib cell view t)
    cadexCV=car(target)
    cadexWindow=cadr(target)
    cadexRunDir=runDir
    dirty=dbIsCellViewModified(cadexCV)
    when(save && dirty && !allowExisting
      error("Target has pre-existing unsaved edits; no job ran. Whole-view save requires explicit authorization"))
    when(save
      unless(view=="schematic" error("Managed check/save currently supports schematics only"))
      baseline=cadexCheck()
      unless(car(baseline)==0 error("Baseline schematic errors; no job ran"))
    )
    outcome=errset(load(path) t)
    unless(outcome error("Managed job failed; inspect partial state before retrying"))
    when(save
      finalCounts=cadexCheck()
      unless(car(finalCounts)==0 && cadr(finalCounts)<=cadr(baseline)
        error("Schematic checker regression; changes remain open and unsaved"))
      cadexJobAssertConnections()
      unless(dbSave(cadexCV) error("Save failed; edits remain open"))
      saved=t
    )
    ; Frame new editors only. Existing viewports and focus belong to the user.
    when(caddr(target) && cadexCV~>bBox hiZoomIn(cadexWindow cadexCV~>bBox))
    hiRedraw(cadexWindow)
    list(lib cell view dirty baseline finalCounts saved cadexResult
      unless(inspection cadexDescribe()))
  )
)

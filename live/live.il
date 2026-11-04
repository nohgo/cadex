; Loaded only by an explicit CIW bootstrap. No batch driver and no exit().
unless(boundp('cadexLiveState) cadexLiveState=nil)

procedure(cadexLiveInit(id token host pid)
  cadexLiveState=list(id token host pid)
)
procedure(cadexLiveIdentity() cadexLiveState)
procedure(cadexLiveRevoke(token)
  when(cadexLiveState && cadr(cadexLiveState)==token cadexLiveState=nil)
)
procedure(cadexLiveInstance(cv name)
  let((matches)
    matches=setof(inst cv~>instances inst~>name==name)
    unless(length(matches)==1 error("Expected exactly one instance named %s" name))
    unless(car(matches)~>objType=="inst" error("Named object is not a single instance: %s" name))
    car(matches)
  )
)
procedure(cadexLiveParameter(inst name)
  let((cdf param)
    cdf=cdfGetInstCDF(inst)
    unless(cdf error("Instance %s has no CDF" inst~>name))
    param=cdfFindParamByName(cdf name)
    unless(param error("No CDF parameter %s on %s" name inst~>name))
    list(cdf param)
  )
)
procedure(cadexLiveRun(token lib cell view operations save)
  let((win cv reused result pair inst param before after type)
    unless(cadexLiveState && cadr(cadexLiveState)==token error("Cadex session was revoked or changed"))
    unless(member(view list("schematic" "layout")) error("Unsupported editor view"))
    ; Resolve the exact existing view BEFORE any append-mode open: typos never create data.
    unless(ddGetObj(lib cell view) error("Existing target not found: %s/%s/%s" lib cell view))
    foreach(w hiGetWindowList()
      pair=errset(geGetEditCellView(w) nil)
      when(pair && car(pair)
        cv=car(pair)
        when(cv~>libName==lib && cv~>cellName==cell && cv~>viewName==view
          unless(win win=w)
        )
      )
    )
    reused=if(win then t else nil)
    unless(win
      type=if(view=="layout" then "maskLayout" else "schematic")
      ; deOpenCellView opens existing data and honors write locks. No mode w,
      ; dbReopen, lock override, or borrowed database reference is used.
      win=deOpenCellView(lib cell view type nil "a")
      unless(win error("Cannot open existing editable view (possibly write-locked): %s/%s/%s" lib cell view))
    )
    cv=geGetEditCellView(win)
    unless(cv error("No editable cellview in target window"))
    unless(cv~>libName==lib && cv~>cellName==cell && cv~>viewName==view error("Target identity mismatch"))
    unless(member(cv~>mode list("a" "w")) error("Target is not writable; refusing mode change or lock override"))
    ; Validate EVERY named object and parameter before the first design mutation.
    foreach(op operations
      inst=cadexLiveInstance(cv cadr(op))
      case(car(op)
        ("move"
          unless(length(caddr(op))==2 error("Expected two origin coordinates"))
          when(cadddr(op) && inst~>xy!=cadddr(op) error("Origin changed since expected readback: %s" inst~>name))
        )
        ("parameter"
          pair=cadexLiveParameter(inst caddr(op))
          unless(isCallable('vfoSetParam) error("vfoSetParam unavailable; refusing to bypass CDF callbacks"))
          when(length(op)>4 && nth(4 op)!=nil && cadr(pair)~>value!=nth(4 op)
            error("Parameter changed since expected readback: %s" inst~>name)
          )
        )
        ("inspect" t)
        (t error("Unsupported live operation"))
      )
    )
    foreach(op operations
      inst=cadexLiveInstance(cv cadr(op))
      case(car(op)
        ("move"
          before=inst~>xy
          inst~>xy=caddr(op)
          after=inst~>xy
          unless(after==caddr(op) error("Origin readback mismatch; inspect partial result"))
          result=cons(list("move" inst~>name before after) result)
        )
        ("parameter"
          pair=cadexLiveParameter(inst caddr(op))
          before=cadr(pair)~>value
          vfoSetParam(car(pair) caddr(op) cadddr(op))
          pair=cadexLiveParameter(inst caddr(op))
          after=cadr(pair)~>value
          result=cons(list("parameter" inst~>name caddr(op) before after) result)
        )
        ("inspect"
          pair=cdfGetInstCDF(inst)
          param=when(pair mapcar(lambda((p) list(p~>name sprintf(nil "%L" p~>type) p~>value sprintf(nil "%L" p~>units))) pair~>parameters))
          result=cons(list("inspect" inst~>name inst~>libName inst~>cellName inst~>xy param) result)
        )
      )
    )
    when(save unless(dbSave(cv) error("Save failed; edits remain open for review")))
    hiRedraw(win)
    ; No close, quit, selection, current-window switch, or automatic save.
    list(lib cell view cv~>mode reused reverse(result) if(save then t else nil))
  )
)

program GLDIAL(input,output,pastel);(*=s7,l3,u+,Y+*)
(************************************************************)
(* ГЛИССАДА-6. ТЕКСТОВЫЙ ДИАЛОГ. ПЕЧАТЬ - ПАСКАЛЬ.             *)
(* ЯДРО - ФОРТРАН: GLINITD, GLPROIZ, GLAUTO, GLNUMR, GLOUT.   *)
(************************************************************)
const H=0.1; RAD=57.2958; NL=41;
type VEC13=array[1..13] of real;
     VEC4=array[1..4] of real;
     Bitset=set of 0..47;
     ARG=record
       buflen,inplen,dummy1,dummy2:integer;
       A:packed array[1..140] of char
     end;
var X,VX1,VX2,VX3,VK1,VK2,VK3,VK4:VEC13;
    U:VEC4; B:ARG; CMD:alfa;
    T,TMAX,RSEED,SIGW,DT0,DTSH,TAU,SUME,EGLI,DTM,ZERO,AVY:real;
    QN,VA,ALF,TH,GA,PS,VTHR,VHCR,ERMAX,ERR:real;
    EPSKM,HNEW,KMHMIN,KMHMAX,KMSF,KMEXP,PFL:real; KMTRY:integer;
    TCTRL,DTCTRL:real; UHOLD:VEC4;
    DTCV,DTB,DTN,DTX,DTD,DTU:real;
    KTIP,MODE,ICTRL,NFR,IFLIB,NPRN,NMAX,NSTP,NEGL,IPOS:integer;
    I,J,IH,JA,JG,IB,K,OCE:integer; OK,RUN,PAUS:boolean;
    IMODE,IEX,IFLT:integer;
    IFL,IGR,ISP:integer; (* закрылки, шасси, спойлеры *)
    ICTLV:integer; (* переключатель шага *)
    MANUAL:boolean; DE,DA,DR,DTZ:real;
    IPILOT,NPILOT:integer; (* 0 - выкл., >0 - шаги запроса *)
    HPAGE:integer; (* номер страницы справки HLP *)
    HOTKEY:boolean; (* однолитерные алиасы включены *)
    PILPAZ:boolean; (* мы стоим в пилотной паузе *)
    RABS:real; (* число из абсолютной команды *)
    RECON:boolean; NFRMX,NEVMX,NSTEP,IEVK:integer;
    RX:VEC13; RU:VEC4; RT:real;
    XP,YP,HP,XK,YK,HK,ZG,PR,RMIN:real;
    FCUR,FSTA,FCAP,FRES,FWRN:real;
    FEX,FRM,FZERO:real; FMODE:integer;
    IREL,IST:integer; RELHIT:boolean;
    SCVERT,SCTOCH,SCY,SCSKO,SCUPR,SCPLAV,SCTOT:real; SCZACH:integer;
    SCW1,SCW2,SCW3,SCW4,SCW5,SCW6,SCW7:real;
    SCQ1,SCQ2,SCQ3,SCQ4,SCQ5,SCQ6:real;
    EXKTIP:array[1..5] of integer;
    EXSIGW,EXRSEED,EXDT0,EXTMAX:array[1..5] of real;
    pastel: array[0..25] of Bitset;
(* диалог *)
procedure PASRED(var D:ARG); external;
(* ядро *)
procedure INITD(var K:integer); fortran;
procedure PROIZV(var X:VEC13; var U:VEC4; var XD:VEC13); fortran;
procedure GLAUTO(var X:VEC13; var U:VEC4); fortran;
procedure PROGC(var T:real; var U:VEC4); fortran;
procedure TURB; fortran;
procedure KUTMER(var X:VEC13; var U:VEC4; var DT,ERR:real); fortran;
procedure KUTMAD(var X:VEC13; var U:VEC4; var DT,EPS:real;
           var HNEW,ERR:real; var IFAIL:integer); fortran;
procedure KMRK4(var X:VEC13; var U:VEC4; var H:real); fortran;
procedure KMPAR(var EPS,HMN,HMX,SF:real;
           var NT:integer; var EX:real); fortran;
procedure KMPAR2(var PF:real); fortran;
procedure KMSET(var EPS:real); fortran;
procedure KMSETP(var PF:real); fortran;
procedure DTPAR(var DTB,DTN,DTX,DTD,DTU:real); fortran;
procedure DTADJ(var ERR,DT:real); fortran;
procedure GLFINJ(var K:integer; var U:VEC4); fortran;
procedure GLFCLR; fortran;
(* конфигурация самолёта: переключатели в /CONFG/ *)
procedure CFSET(var IFL,IGR,ISP:integer); fortran;
procedure CFGET(var IFL,IGR,ISP:integer); fortran;
(* регистратор: параметры в /RECPAR/ *)
procedure RCGPAR(var NF,NE,NS:integer); fortran;
procedure RCSPAR(var NF,NE,NS:integer); fortran;
procedure RECCLR; fortran;
procedure RECPUT(var X:VEC13; var U:VEC4; var T:real); fortran;
procedure RCEVT(var K:integer; var T:real); fortran;
procedure RCN(var NF,NEV:integer); fortran;
procedure RCGET(var J:integer; var X:VEC13; var U:VEC4;
           var T:real); fortran;
procedure RCEGET(var J,K:integer; var T:real); fortran;
(* оценка задания *)
procedure SCCLR; fortran;
procedure SCPUT(var U:VEC4); fortran;
procedure SCCALC(var X:VEC13); fortran;
procedure SCGET(var RV,RT,RY,SS,UP,PP,TT:real; var IS:integer); fortran;
procedure SCWPAR(var WV,WT,WY,WG,WU,WP,PL:real); fortran;
procedure SCQGET(var V1,V2,V3,V4,V5,V6:real); fortran;
procedure PRVIN; fortran;
procedure JUDG(var X:VEC13); fortran;
(* аксессоры GLACC *)
procedure GLSET(var T,DT:real; var K,M,IC,NR,IFL:integer;
           var TM:real); fortran;
procedure GLT(var T:real); fortran;
procedure GLSOST(var VTH,HCR:real); fortran;
procedure GLSEED(var RS:real); fortran;
procedure GLBUR(var SIG,TAU,WX,WY,WZ:real); fortran;
procedure GLSC(var SU:real; var NE:integer); fortran;
procedure GLVOD(var VA,ALF:real); fortran;
procedure GLANG(var X:VEC13; var TH,GA,PS,DTM,EG:real;
           var IP:integer); fortran;
(* рельеф: все расчёты - в Фортране, Паскаль только печатает *)
procedure RELGET(var X11,X12,ALT:real; var IR:integer;
           var ZG,PR,RMIN:real); fortran;
procedure ZEM(var X11,X12,ZG:real); fortran;
(* запас топлива: расчёт в Фортране *)
procedure FUELRS(var MODE:integer; var DT,U4:real); fortran;
procedure FUELSE(var FEX,FRM:real); fortran;
procedure FUELGT(var FCUR,FSTA,FCAP,FRES,FWRN:real); fortran;
procedure MNPRS(var X11,X12,ALT,T:real); fortran;
procedure STK(var X0,Y0,H0,X1,Y1,H1:real; var IST:integer;
           var XK,YK,HK:real); fortran;
(************************************************************)
procedure GTINT(var N:integer; var OK:boolean);
var P:integer; C:char;
begin
  OK:=true; N:=0; P:=1;
  while (P<=B.INPLEN) and (B.A[P]=' ') do P:=P+1;
  if P>B.INPLEN then begin OK:=false; exit end;
  while P<=B.INPLEN do
  begin
    C:=B.A[P];
    if (C<'0') or (C>'9') then begin OK:=false; exit end;
    N:=N*10+ord(C)-48; P:=P+1
  end
end;
(************************************************************)
procedure GTRL(var R:real; var OK:boolean);
var P,S:integer; F:real; C:char;
begin
  OK:=true; P:=1;
  while (P<=B.INPLEN) and (B.A[P]=' ') do P:=P+1;
  S:=1;
  if P<=B.INPLEN then
    if B.A[P]='-' then begin S:=-1; P:=P+1 end
    else if B.A[P]='+' then P:=P+1;
  R:=0; F:=1;
  while P<=B.INPLEN do
  begin
    C:=B.A[P];
    if C='.' then
    begin
      P:=P+1;
      while P<=B.INPLEN do
      begin
        C:=B.A[P];
        if (C<'0') or (C>'9') then begin OK:=false; exit end;
        R:=R*10+ord(C)-48; F:=F*10; P:=P+1
      end
    end
    else
    begin
      if (C<'0') or (C>'9') then begin OK:=false; exit end;
      R:=R*10+ord(C)-48; P:=P+1
    end
  end;
  R:=S*R/F
end;
(************************************************************)
(* Число для абсолютной команды: литеры 1..3 - префикс "DE=",  *)
(* число начинается с позиции 4 и продолжается до конца ввода. *)
procedure GTNUM4(var R:real; var OK:boolean);
var P,S:integer; F:real; C:char;
begin
  OK:=true; P:=4;
  if P>B.INPLEN then begin OK:=false; exit end;
  S:=1;
  if B.A[P]='-' then begin S:=-1; P:=P+1 end
  else if B.A[P]='+' then P:=P+1;
  R:=0; F:=1;
  while P<=B.INPLEN do
  begin
    C:=B.A[P];
    if C='.' then
    begin
      P:=P+1;
      while P<=B.INPLEN do
      begin
        C:=B.A[P];
        if (C<'0') or (C>'9') then begin OK:=false; exit end;
        R:=R*10+ord(C)-48; F:=F*10; P:=P+1
      end
    end
    else
    begin
      if (C<'0') or (C>'9') then begin OK:=false; exit end;
      R:=R*10+ord(C)-48; P:=P+1
    end
  end;
  R:=S*R/F
end;
(************************************************************)
procedure GTALF(var A:alfa);
var P:integer;
begin
  for P:=1 to 6 do
    if P<=B.INPLEN then A[P]:=B.A[P] else A[P]:=' '
end;
(************************************************************)
procedure ASK;
begin
  writeln;
  (* В пилотном режиме одна литера приглашения вместо двух знаков. *)
  if IMODE=0 then write('>') else write('> ');
  B.BUFLEN:=80; B.INPLEN:=0;
  PASRED(B)
end;
(************************************************************)
procedure PARAMS;
begin
  writeln('GLISSADA-6 / TEKSTOVY DIALOG');
  writeln('TIP 1..5 :'); ASK; GTINT(KTIP,OK);
  writeln('MODE 1 AVTO / 2 PROG :'); ASK; GTINT(MODE,OK);
  writeln('ICTRL 0 BATCH / 1 TERM :'); ASK; GTINT(ICTRL,OK);
  writeln('NFR SEK :'); ASK; GTINT(NFR,OK);
  writeln('IFLIB 0/1 :'); ASK; GTINT(IFLIB,OK);
  writeln('TMAX :'); ASK; GTRL(TMAX,OK);
  writeln('RSEED :'); ASK; GTRL(RSEED,OK);
  writeln('SIGW :'); ASK; GTRL(SIGW,OK);
  writeln('DT0 :'); ASK; GTRL(DT0,OK)
end;
(************************************************************)
procedure INIT;
begin
  KMPAR(EPSKM,KMHMIN,KMHMAX,KMSF,KMTRY,KMEXP);
  KMPAR2(PFL);
  TCTRL:=0.0; DTCTRL:=H;
  GLFCLR;
  RECCLR; SCCLR;
  MANUAL:=false; DE:=0.0; DA:=0.0; DR:=0.0; DTZ:=DT0;
  DTSH:=H; TAU:=1.0; ZERO:=0.0;
  GLSET(ZERO,DTSH,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX);
  GLSEED(RSEED);
  GLBUR(SIGW,TAU,ZERO,ZERO,ZERO);
  INITD(KTIP);
  GLSOST(VTHR,VHCR);
  X[1]:=VTHR; X[2]:=0.0; X[3]:=0.0;
  X[4]:=1.0; X[5]:=0.0; X[6]:=0.0; X[7]:=0.0;
  X[8]:=0.0; X[9]:=0.0; X[10]:=0.0;
  X[11]:=-15000.0; X[12]:=0.0; X[13]:=15000.0*0.05241;
  T:=0.0;
  for I:=1 to 3 do U[I]:=0.0;
  U[4]:=DT0;
  SUME:=0.0; NEGL:=0; NSTP:=0;
  if MODE=2 then PRVIN;
  NPRN:=trunc(NFR/DTSH); if NPRN<1 then NPRN:=999999;
  NMAX:=trunc(TMAX/DTSH)
end;
(************************************************************)
procedure DOSTP;
var I,IFAIL:integer; ZGL:real; RECTRL:boolean;
begin
  XP:=X[11]; YP:=X[12]; HP:=X[13];
  RECTRL:=false;
  if (ICTRL<>3) and (ICTRL<>4) then
  begin
    T:=T+DTSH;
    GLSET(T,DTSH,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX);
    if MANUAL then
    begin
      U[1]:=DE; U[2]:=DA; U[3]:=DR; U[4]:=DTZ
    end
    else if MODE=1 then GLAUTO(X,U) else PROGC(T,U)
  end
  else
  begin
    if T>=TCTRL then
    begin
      if MANUAL then
      begin
        U[1]:=DE; U[2]:=DA; U[3]:=DR; U[4]:=DTZ
      end
      else if MODE=1 then GLAUTO(X,U) else PROGC(T,U);
      for I:=1 to 4 do UHOLD[I]:=U[I];
      TCTRL:=T+DTCTRL;
      if ICTRL=4 then RECTRL:=true
    end
    else for I:=1 to 4 do U[I]:=UHOLD[I]
  end;
  FMODE:=1;
  FUELRS(FMODE,DTSH,U[4]);
  SCPUT(U);
  TURB;
  if ICTRL=3 then
  begin
    KUTMAD(X,U,DTSH,EPSKM,HNEW,ERR,IFAIL);
    DTSH:=HNEW;
    if ERR>ERMAX then ERMAX:=ERR;
    T:=T+DTSH;
    GLSET(T,DTSH,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX);
    KMRK4(X,U,DTSH)
  end
  else
  begin
    if ICTRL=4 then
    begin
      T:=T+DTSH;
      GLSET(T,DTSH,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX)
    end;
    if ICTRL>=2 then
    begin
      KUTMER(X,U,DTSH,ERR);
      if ERR>ERMAX then ERMAX:=ERR;
      if RECTRL then DTADJ(ERR,DTCTRL)
    end;
    PROIZV(X,U,VK1);
    for I:=1 to 13 do VX1[I]:=X[I]+0.5*DTSH*VK1[I];
    PROIZV(VX1,U,VK2);
    for I:=1 to 13 do VX2[I]:=X[I]+0.5*DTSH*VK2[I];
    PROIZV(VX2,U,VK3);
    for I:=1 to 13 do VX3[I]:=X[I]+DTSH*VK3[I];
    PROIZV(VX3,U,VK4);
    for I:=1 to 13 do
      X[I]:=X[I]+DTSH*(VK1[I]+2*VK2[I]+2*VK3[I]+VK4[I])/6.0
  end;
  QN:=sqrt(X[4]*X[4]+X[5]*X[5]+X[6]*X[6]+X[7]*X[7]);
  X[4]:=X[4]/QN; X[5]:=X[5]/QN; X[6]:=X[6]/QN; X[7]:=X[7]/QN;
  EGLI:=X[13]+0.05241*X[11];
  SUME:=SUME+EGLI*EGLI; NEGL:=NEGL+1;
  MNPRS(X[11],X[12],X[13],T);
  STK(XP,YP,HP,X[11],X[12],X[13],IST,XK,YK,HK);
  if IST=1 then
  begin
    ZEM(XK,X[12],ZGL);
    if ZGL>0.5 then
    begin
      X[11]:=XK; X[12]:=YK; X[13]:=HK; RELHIT:=true
    end;
  end;
  NSTP:=NSTP+1;
  if RECON and (NSTP mod NSTEP=0) then RECPUT(X,U,T)
end;
(************************************************************)
(* Пробелы до нужной позиции в строке кадра.                   *)
procedure PAD(N:integer);
var K:integer;
begin
  for K:=1 to N do write(' ')
end;
(************************************************************)
(* Печать действительного числа в натуральном виде: знак,     *)
(* целая часть, явная точка, один знак после запятой.         *)
(* W - полная ширина поля вместе со знаком и точкой.          *)
procedure PRNUM(R:real; W:integer);
var N,IP,FP,S,WW,K,ND:integer;
begin
  S:=1;
  if R<0.0 then S:=-1;
  N:=TRUNC(ABS(R)*100.0+0.5);
  IP:=N div 100;
  FP:=N mod 100;
  if S<0 then write('-') else write(' ');
  write(IP:1);
  if FP<10 then
  begin
    write('.0');
    write(FP:1)
  end
  else write('.',FP:1);
  ND:=1;
  K:=IP div 10;
  while K>0 do
  begin
    ND:=ND+1;
    K:=K div 10
  end;
  WW:=W-3-ND;
  for K:=1 to WW do write(' ')
end;
(************************************************************)
procedure PRFRM;
var I,J,IH,JA,IB:integer; HGL,ZGL,XX:real;
begin
  GLANG(X,TH,GA,PS,DTM,EGLI,IPOS);
  GLVOD(VA,ALF);
  RELGET(X[11],X[12],X[13],IREL,ZG,PR,RMIN);
  FUELGT(FCUR,FSTA,FCAP,FRES,FWRN);
  IB:=21+TRUNC(X[12]/5.0);
  if IB<1 then IB:=1;
  if IB>41 then IB:=41;
  JA:=31-TRUNC(DTM/500.0);
  writeln;
  writeln('T=',T:7:1,' TIP=',KTIP:1,' DALN=',DTM:7:0,
          ' VYS=',X[13]:7:1,' Y=',X[12]:7:1);
  writeln(' VYS PROFILE             + PLAN SVERHU');
  for IH:=12 downto 0 do
  begin
    write(' ',IH*100:4,' +');
    for J:=1 to 30 do
    begin
      HGL:=0.05241*(31-J)*500.0;
      ZGL:=-1.0;
      if IREL=1 then
      begin
        XX:=-(31-J)*500.0;
        ZEM(XX,X[12],ZGL)
      end;
      if (IH=TRUNC(X[13]/100.0)) and (J=JA) then write('*')
      else if (IREL=1) and (IH=TRUNC(ZGL/100.0)) then write('T')
      else if TRUNC(HGL/100.0)=IH then write('.')
      else if IH=0 then write('=')
      else write(' ')
    end;
    write(' +');
    if IH=12 then
    begin
      write('    +====+');
      for J:=1 to IB do write(' ');
      write('*'); writeln
    end
    else if IH=0 then writeln('    +====+')
    else writeln('    +    +')
  end;
  writeln('     15km  10km  5km  0');
  (* Нижние строки: две колонки по 38 знаков, между ними плюс. *)
  (* Слева глиссада, курс, скорость; справа земля, просвет, минимум. *)
  write(' GLISS 3 GR +----*----+ EGLI='); PRNUM(EGLI,7); write(' M');
  write('+');
  if IREL=1 then
  begin
    write(' ZEMLYA='); PAD(1); PRNUM(ZG,7); write(' M'); PAD(20)
  end
  else PAD(38);
  writeln;
  write(' KURS LUCH +----*----+ Y='); PAD(4); PRNUM(X[12],7);
  write(' M');
  write('+');
  if IREL=1 then
  begin
    write(' PROSVET='); PRNUM(PR,7); write(' M'); PAD(20)
  end
  else PAD(38);
  writeln;
  write(' SKOR='); PAD(1); PRNUM(VA,7);
  write(' VERT='); PAD(1); PRNUM(X[2],7); PAD(10);
  write('+');
  if IREL=1 then
  begin
    write(' MIN='); PAD(4); PRNUM(RMIN,7); write(' M'); PAD(20)
  end
  else PAD(38);
  writeln;
  write(' ATAKA='); PRNUM(ALF,7);
  write(' TYAG='); PRNUM(100*U[4],7); PAD(11);
  write('+');
  write(' TOPLIVO='); PRNUM(FCUR,7); write(' KG');
  if FCUR<=FWRN then begin write(' MALO'); PAD(14) end
  else PAD(19);
  writeln;
  write(' KONF F',IFL:1,' G',IGR:1,' S',ISP:1); PAD(24);
  write('+');
  write(' REZERV='); PRNUM(FRES,7); write(' KG');
  PAD(20);
  writeln;
  (* Углы из GLANG уже в градусах; справа - фактические рули. *)
  write(' TANG='); PRNUM(TH,5); write(' KREN='); PRNUM(GA,5);
  write(' KURS='); PRNUM(PS,5); PAD(2);
  write('+');
  write(' DE='); PRNUM(DE,5); write(' DA='); PRNUM(DA,5);
  write(' DR='); PRNUM(DR,5); PAD(8);
  writeln
end;
(************************************************************)
procedure SCRROW(NM:alfa; V,Q,W:real);
begin
  write(NM,V:10:2,Q:8:2,W:6:2,' ');
  if Q>=0.9 then begin writeln('ОТЛ'); exit end;
  if Q>=0.7 then begin writeln('ХОР'); exit end;
  if Q>=0.4 then begin writeln('УДВ'); exit end;
  writeln('НЕУД')
end;
(************************************************************)
procedure PRTSCR;
begin
  SCGET(SCVERT,SCTOCH,SCY,SCSKO,SCUPR,SCPLAV,SCTOT,SCZACH);
  SCWPAR(SCW1,SCW2,SCW3,SCW4,SCW5,SCW6,SCW7);
  SCQGET(SCQ1,SCQ2,SCQ3,SCQ4,SCQ5,SCQ6);
  writeln('ДЕБРИФИНГ ЗАДАНИЯ');
  writeln('КОМПОНЕНТ   ЗНАЧЕНИЕ КАЧЕСТВО ВЕС СТАТУС');
  SCRROW('ВЕРТ  ',SCVERT,SCQ1,SCW1);
  SCRROW('ТОЧКА ',SCTOCH,SCQ2,SCW2);
  SCRROW('ОТ ОСИ',SCY,SCQ3,SCW3);
  SCRROW('СКО   ',SCSKO,SCQ4,SCW4);
  SCRROW('ПЕРЕУП',SCUPR,SCQ5,SCW5);
  SCRROW('НЕПЛАВ',SCPLAV,SCQ6,SCW6);
  writeln('ИТОГО БАЛЛ=',SCTOT:7:3,' ПОРОГ=',SCW7:5:2,
          ' ЗАЧЕТ=',SCZACH:1)
end;
(************************************************************)
procedure PLYREC;
var J,NF,NEV,KEV:integer; TEV:real;
begin
  RCN(NF,NEV);
  writeln('FRAMES=',NF:1,' EVENTS=',NEV:1,' NSTEP=',NSTEP:1);
  for J:=1 to NF do
  begin
    RCGET(J,RX,RU,RT);
    writeln('TELE',J:4,' T=',RT:9:2);
    writeln('  X=',RX[1]:11:4,RX[2]:11:4,RX[3]:11:4,
            RX[4]:11:5,RX[5]:11:5);
    writeln('     ',RX[6]:11:5,RX[7]:11:5,RX[8]:11:5,
            RX[9]:11:5,RX[10]:11:5);
    writeln('     ',RX[11]:11:2,RX[12]:11:3,RX[13]:11:3);
    writeln('  U=',RU[1]:11:5,RU[2]:11:5,RU[3]:11:5,RU[4]:11:5)
  end;
  for J:=1 to NEV do
  begin
    RCEGET(J,KEV,TEV);
    writeln('EV  ',J:4,' K=',KEV:1,' T=',TEV:9:2)
  end
end;
(************************************************************)
(* Справка оператора-пилота: печать страницы P (1..3). *)
procedure HELP(P:integer);
var N,NZ:integer;
begin
  writeln;
  if P=1 then
  begin
    writeln('СПРАВКА 1/3 - ПИЛОТ: УПРАВЛЕНИЕ');
    writeln('STA ПУСК  STE ШАГ 0.1 С  STO ОСТАНОВ');
    writeln('PAR ПАРАМЕТРЫ И ПЕРЕЗАПУСК  PRN КАДР');
    writeln('AUTO АВТОПИЛОТ: РУЛИ В НУЛЬ  INS ИНСТРУКТОР');
    writeln('EXIT ВЫХОД');
    if HOTKEY then
    begin
      writeln('ГОРЯЧИЕ КЛАВИШИ: ОДНА ЛИТЕРА + ENTER');
      writeln('E/Q ВЫСОТА  W/S ЭЛЕРОНЫ  A/D НАПР.  R/F ТЯГА');
      writeln('X ПАУЗА  P КАДР  N НЕЙТРАЛЬ  T ТРИМ');
      writeln('1/2/3 СПРАВКА; ПОЛНЫЙ ВВОД ТОЖЕ РАБОТАЕТ')
    end;
    writeln('EV+ EV- DE РУЛЬ ВЫСОТЫ ШАГ 0.05 ПРЕДЕЛ +/-0.30');
    writeln('AI+ AI- DA ЭЛЕРОНЫ  ШАГ 0.05 ПРЕДЕЛ +/-0.15');
    writeln('RU+ RU- DR РУЛЬ НАПР. ШАГ 0.05 ПРЕДЕЛ +/-0.20');
    writeln('TH+ TH- DTZ ТЯГА    ШАГ 0.05 ПРЕДЕЛ 0.00..1.00');
    writeln('АБСОЛЮТНО: DE=Z -0.30..0.30 DA=Z -0.15..0.15');
    writeln('           DR=Z -0.20..0.20 TH=Z 0.00..1.00');
    writeln('ЕДИНИЦЫ: DE/DA/DR - ДОЛИ, DTZ - ДОЛЯ ТЯГИ');
    writeln('TRIM РУЛИ В НУЛЬ, ТЯГА СОХРАНЕНА');
    writeln('NEUT ВСЁ В НУЛЬ И АВТОПИЛОТ');
    writeln('PILOT 0 - ЗАПРОС ВЫКЛЮЧЕН; 1..100 - ШАГОВ');
    writeln('МЕЖДУ ЗАПРОСАМИ К ПИЛОТУ. НА ЗАПРОСЕ:');
    writeln('КАДР, ПАУЗА И ОЖИДАНИЕ КОМАНДЫ; ДАЛЕЕ');
    writeln('ПОЛЁТ ПРОДОЛЖАЕТСЯ, КРОМЕ STO/EXIT/FRZ/PILOT')
  end
  else if P=2 then
  begin
    writeln('СПРАВКА 2/3 - ИНСТРУКТОР');
    writeln('SEL 1..5 ВЫБРАТЬ УПРАЖНЕНИЕ T1..T5');
    writeln('FRZ ЗАМОРОЗКА  UNF СНЯТЬ ЗАМОРОЗКУ');
    writeln('INJ 1..5 ВВЕСТИ ОТКАЗ');
    writeln('ICTL 0/3/4 ШАГ: ФИКС/ИНТЕГР/УПРАВЛЕНИЕ');
    writeln('EPS >0 ДОПУСК ОШИБКИ, ПОРОГ АДАПТАЦИИ');
    writeln('PFL >0 ПОРОГ ОТНОСИТЕЛЬНОЙ НОРМЫ ОШИБКИ');
    writeln('DTC 0.02..0.50 ШАГ УПРАВЛЕНИЯ ВРУЧНУЮ');
    writeln('FUL >=0 КГ ДОПОЛНИТЕЛЬНОЕ ТОПЛИВО');
    writeln('RES >0 МНОЖИТЕЛЬ РЕЗЕРВА ТОПЛИВА');
    writeln('FLP 0/1/2 ЗАКРЫЛКИ: УБРАНЫ/ВЗЛЁТ/ПОСАДКА');
    writeln('GER 0/1 ШАССИ: УБРАНО/ВЫПУЩЕНО');
    writeln('SPL 0/1 СПОЙЛЕРЫ: УБРАНЫ/ВЫПУЩЕНЫ');
    writeln('REC ЗАПИСЬ  RPL ВОСПРОИЗВЕДЕНИЕ');
    writeln('RST ОЧИСТКА ЗАПИСИ  SCR ДЕБРИФИНГ');
    writeln('PIL РЕЖИМ ПИЛОТА  EXIT ВЫХОД');
    writeln('PILOT 0..100 КАДЕНЦИЯ ЗАПРОСА К ПИЛОТУ');
    writeln('HLP 1/2/3 - ЭТА СПРАВКА: ПИЛОТ/ИНСТРУКТОР/ЗАДАНИЕ')
  end
  else if P=3 then
  begin
    writeln('СПРАВКА 3/3 - ПОЛЁТНОЕ ЗАДАНИЕ');
    if KTIP=1 then writeln('САМОЛЁТ: МИГ-15')
    else if KTIP=2 then writeln('САМОЛЁТ: ИЛ-28')
    else if KTIP=3 then writeln('САМОЛЁТ: ТУ-104')
    else if KTIP=4 then writeln('САМОЛЁТ: АН-24')
    else if KTIP=5 then writeln('САМОЛЁТ: АН-2')
    else writeln('САМОЛЁТ: НЕИЗВЕСТНЫЙ ТИП');
    writeln('MODE=',MODE:1,' ICTRL=',ICTRL:1,' KTIP=',KTIP:1);
    writeln('SIGW=',SIGW:6:2,' RSEED=',RSEED:8:1);
    writeln('DT0=',DT0:5:2,' TMAX=',TMAX:7:0,' С');
    NZ:=0;
    for N:=1 to 5 do
      if (KTIP=EXKTIP[N]) and (abs(SIGW-EXSIGW[N])<0.0001) and
         (abs(RSEED-EXRSEED[N])<0.0001) and
         (abs(DT0-EXDT0[N])<0.0001) and
         (abs(TMAX-EXTMAX[N])<0.0001) then NZ:=N;
    if NZ>0 then
      writeln('ЗАДАНИЕ T',NZ:1,' ОПРЕДЕЛЕНО ПО EX-МАССИВАМ')
    else writeln('ЗАДАНИЕ T1..T5 НЕ ОПРЕДЕЛЕНО');
    writeln('СЦЕНАРИЙ:');
    if NZ=1 then writeln('ТУ-104 ШТИЛЬ, ТОЧНАЯ ПОСАДКА')
    else if NZ=2 then writeln('МИГ-15 1952 ГРОЗА У АЭРОДРОМА')
    else if NZ=3 then writeln('ИЛ-28 1958 СЛОЖНЫЕ МЕТЕОУСЛОВИЯ')
    else if NZ=4 then writeln('АН-24 2010 ТУМАН, ИГАРКА')
    else if NZ=5 then writeln('АН-2 УМЕРЕННАЯ ТУРБУЛЕНТНОСТЬ');
    writeln('ЦЕЛЬ: VERT<=4.0  TCH>=0  OCENKA<=3')
  end
end;
(************************************************************)
procedure CMDLOOP(var CMD:alfa);
begin
  if IMODE=0 then
  begin
    writeln('PIL: STA STE STO PAR PRN AUTO INS EXIT');
    writeln('MAN: EV+ EV- AI+ AI- RU+ RU- TH+ TH-');
    writeln('     DE=Z DA=Z DR=Z TH=Z TRIM NEUT');
    if HOTKEY then writeln('ЛИТЕРЫ: E Q W S A D R F X P N T 1 2 3')
  end
  else
    writeln('INS: SEL/FRZ/UNF/INJ/EPS/REC/RPL/RST/SCR');
    writeln('     FUL/RES/HLP/PIL/PILOT FLP/GER/SPL ICTL');
    writeln('HLP 1/2/3 - СПРАВКА ПИЛОТ/ИНСТРУКТОР/ЗАДАНИЕ');
  ASK; GTALF(CMD);
  (* Абсолютные команды: префикс DE=/DA=/DR=/TH=, число после него. *)
  (* Приводим их к 6-литерному виду для обычного разбора в select.  *)
  if B.INPLEN>=3 then
    if (B.A[1]='D') and (B.A[2]='E') and (B.A[3]='=') then
      CMD:='DE=   '
    else if (B.A[1]='D') and (B.A[2]='A') and (B.A[3]='=') then
      CMD:='DA=   '
    else if (B.A[1]='D') and (B.A[2]='R') and (B.A[3]='=') then
      CMD:='DR=   '
    else if (B.A[1]='T') and (B.A[2]='H') and (B.A[3]='=') then
      CMD:='TH=   ';
  (* Справка: HLP или HLP 1/2/3 - номер страницы на той же строке. *)
  HPAGE:=0;
  if B.INPLEN>=3 then
    if (B.A[1]='H') and (B.A[2]='L') and (B.A[3]='P') then
    begin
      CMD:='HLP   ';
      if B.INPLEN>=5 then
        if (B.A[4]=' ') and (B.A[5]>='1') and (B.A[5]<='3') then
          HPAGE:=ord(B.A[5])-48
    end;
  (* Горячие клавиши БЭСМ-6: одна литера + Enter -> полная команда. *)
  (* Многолитерный ввод не меняем: здесь только INPLEN=1.          *)
  if HOTKEY and (B.INPLEN=1) then
  begin
    if CMD='E     ' then CMD:='EV+   '
    else if CMD='Q     ' then CMD:='EV-   '
    else if CMD='W     ' then CMD:='AI+   '
    else if CMD='S     ' then CMD:='AI-   '
    else if CMD='A     ' then CMD:='RU+   '
    else if CMD='D     ' then CMD:='RU-   '
    else if CMD='R     ' then CMD:='TH+   '
    else if CMD='F     ' then CMD:='TH-   '
    else if CMD='X     ' then CMD:='STO   '
    else if CMD='P     ' then CMD:='PRN   '
    else if CMD='N     ' then CMD:='NEUT  '
    else if CMD='T     ' then CMD:='TRIM  '
    else if CMD='1     ' then begin CMD:='HLP   '; HPAGE:=1 end
    else if CMD='2     ' then begin CMD:='HLP   '; HPAGE:=2 end
    else if CMD='3     ' then begin CMD:='HLP   '; HPAGE:=3 end
  end
end;
(************************************************************)
begin
  PASTEL[3]:=[48];
  IFL:=0; IGR:=0; ISP:=0; CFSET(IFL,IGR,ISP);
  RCGPAR(NFRMX,NEVMX,NSTEP);
  IMODE:=0; IEX:=1;
  IPILOT:=0; NPILOT:=10; (* запрос к пилоту по умолчанию выключен *)
  HPAGE:=1; (* справка по умолчанию открывает первую страницу *)
  HOTKEY:=true; (* алиасы включены; false выключает их целиком *)
  PILPAZ:=false;
  EXKTIP[1]:=3; EXSIGW[1]:=0.0; EXRSEED[1]:=7351.0;
  EXDT0[1]:=0.60; EXTMAX[1]:=2400.0;
  EXKTIP[2]:=1; EXSIGW[2]:=1.5; EXRSEED[2]:=7351.5;
  EXDT0[2]:=0.60; EXTMAX[2]:=2400.0;
  EXKTIP[3]:=2; EXSIGW[3]:=0.5; EXRSEED[3]:=7351.5;
  EXDT0[3]:=0.60; EXTMAX[3]:=2400.0;
  EXKTIP[4]:=4; EXSIGW[4]:=0.0; EXRSEED[4]:=7351.5;
  EXDT0[4]:=0.60; EXTMAX[4]:=2400.0;
  EXKTIP[5]:=5; EXSIGW[5]:=0.3; EXRSEED[5]:=7351.5;
  EXDT0[5]:=0.60; EXTMAX[5]:=2400.0;
  PARAMS;
  INIT;
  FEX:=0.0; FRM:=1.0;
  PAUS:=true; RUN:=false; RELHIT:=false; FMODE:=0; FZERO:=0.0;
  FUELRS(FMODE,FZERO,U[4]);
  repeat
    if PAUS then
    begin
      CMDLOOP(CMD);
      select
        CMD='PIL   ': begin IMODE:=0; PAUS:=true end;
        CMD='INS   ': begin IMODE:=1; PAUS:=true end;
        CMD='FRZ   ': begin writeln('FREEZE'); IEVK:=10; RCEVT(IEVK,T);
          RUN:=false; PAUS:=true end;
        CMD='UNF   ': begin writeln('UNFREEZE');
          IEVK:=11; RCEVT(IEVK,T); RUN:=true; PAUS:=false end;
        CMD='SEL   ': begin ASK; GTINT(IEX,OK);
          if (IEX>=1) and (IEX<=5) then
          begin
            KTIP:=EXKTIP[IEX]; SIGW:=EXSIGW[IEX];
            RSEED:=EXRSEED[IEX]; DT0:=EXDT0[IEX];
            TMAX:=EXTMAX[IEX]; INIT;
            writeln('EXERCISE=',IEX:1,' SELECTED')
          end else writeln('NO EXERCISE');
          PAUS:=true end;
        CMD='PFL   ': begin ASK; GTRL(PFL,OK); KMSETP(PFL);
          writeln('PFL=',PFL:10:3) end;
        CMD='EPS   ': begin ASK; GTRL(EPSKM,OK); KMSET(EPSKM);
          writeln('EPS=',EPSKM:10:3) end;
        CMD='FUL   ': begin ASK; GTRL(FEX,OK); FUELSE(FEX,FRM);
          writeln('ДОПОЛНИТЕЛЬНОЕ ТОПЛИВО=',FEX:8:2,' КГ') end;
        CMD='RES   ': begin ASK; GTRL(FRM,OK); FUELSE(FEX,FRM);
          writeln('МНОЖИТЕЛЬ РЕЗЕРВА=',FRM:8:3) end;
        CMD='ICTL  ': begin ASK; GTINT(ICTLV,OK);
          if OK and ((ICTLV=0) or (ICTLV=3) or (ICTLV=4)) then
          begin
            ICTRL:=ICTLV;
            TCTRL:=0.0; DTCTRL:=H; DTSH:=H;
            if ICTLV=0 then writeln('ШАГ ФИКСИРОВАННЫЙ')
            else if ICTLV=3 then writeln('ШАГ ИНТЕГР. АДАПТИВНЫЙ')
            else writeln('ШАГ УПРАВЛЕНИЯ АДАПТИВНЫЙ')
          end
          else writeln('ОШИБКА: ICTL 0/3/4') end;
        CMD='PILOT ': begin ASK; GTINT(NPILOT,OK);
          if OK and (NPILOT>=0) and (NPILOT<=100) then
          begin
            IPILOT:=NPILOT;
            if NPILOT>0 then
              writeln('ЗАПРОС К ПИЛОТУ КАЖДЫЕ ',NPILOT:1,' ШАГОВ')
            else writeln('ЗАПРОС К ПИЛОТУ ВЫКЛЮЧЕН')
          end
          else writeln('ОШИБКА: PILOT 0..100') end;
        CMD='FLP   ': begin ASK; GTINT(IFL,OK);
          if OK and (IFL>=0) and (IFL<=2) then
          begin
            CFSET(IFL,IGR,ISP);
            if IFL=0 then writeln('ЗАКРЫЛКИ: УБРАНЫ')
            else if IFL=1 then writeln('ЗАКРЫЛКИ: ВЗЛЁТНЫЕ')
            else writeln('ЗАКРЫЛКИ: ПОСАДОЧНЫЕ')
          end
          else begin CFGET(IFL,IGR,ISP);
            writeln('ОШИБКА: FLP 0/1/2') end end;
        CMD='GER   ': begin ASK; GTINT(IGR,OK);
          if OK and (IGR>=0) and (IGR<=1) then
          begin
            CFSET(IFL,IGR,ISP);
            if IGR=0 then writeln('ШАССИ: УБРАНО')
            else writeln('ШАССИ: ВЫПУЩЕНО')
          end
          else begin CFGET(IFL,IGR,ISP);
            writeln('ОШИБКА: GER 0/1') end end;
        CMD='SPL   ': begin ASK; GTINT(ISP,OK);
          if OK and (ISP>=0) and (ISP<=1) then
          begin
            CFSET(IFL,IGR,ISP);
            if ISP=0 then writeln('СПОЙЛЕРЫ: УБРАНЫ')
            else writeln('СПОЙЛЕРЫ: ВЫПУЩЕНЫ, ОЦЕНКА')
          end
          else begin CFGET(IFL,IGR,ISP);
            writeln('ОШИБКА: SPL 0/1') end end;
        CMD='DTC   ': begin ASK; GTRL(DTCV,OK);
          DTPAR(DTB,DTN,DTX,DTD,DTU);
          if DTCV<DTN then DTCV:=DTN;
          if DTCV>DTX then DTCV:=DTX;
          DTCTRL:=DTCV;
          writeln('DTC=',DTCTRL:8:3) end;
        CMD='HLP   ': begin
          if (HPAGE<1) or (HPAGE>3) then HPAGE:=1;
          HELP(HPAGE)
        end;
        CMD='AUTO  ': begin MANUAL:=false; DE:=0.0; DA:=0.0; DR:=0.0;
          writeln('AUTO PILOT: РУЛИ В НУЛЕ') end;
        CMD='EV+   ': begin MANUAL:=true; DE:=DE+0.05;
          if DE>0.30 then DE:=0.30; writeln('DE=',DE:6:3) end;
        CMD='EV-   ': begin MANUAL:=true; DE:=DE-0.05;
          if DE< -0.30 then DE:=-0.30; writeln('DE=',DE:6:3) end;
        CMD='AI+   ': begin MANUAL:=true; DA:=DA+0.05;
          if DA>0.15 then DA:=0.15; writeln('DA=',DA:6:3) end;
        CMD='AI-   ': begin MANUAL:=true; DA:=DA-0.05;
          if DA< -0.15 then DA:=-0.15; writeln('DA=',DA:6:3) end;
        CMD='RU+   ': begin MANUAL:=true; DR:=DR+0.05;
          if DR>0.20 then DR:=0.20; writeln('DR=',DR:6:3) end;
        CMD='RU-   ': begin MANUAL:=true; DR:=DR-0.05;
          if DR< -0.20 then DR:=-0.20; writeln('DR=',DR:6:3) end;
        CMD='TH+   ': begin MANUAL:=true; DTZ:=DTZ+0.05;
          if DTZ>1.0 then DTZ:=1.0; writeln('DTZ=',DTZ:6:3) end;
        CMD='TH-   ': begin MANUAL:=true; DTZ:=DTZ-0.05;
          if DTZ<0.0 then DTZ:=0.0; writeln('DTZ=',DTZ:6:3) end;
        CMD='DE=   ': begin GTNUM4(RABS,OK);
            if OK and (RABS>=-0.30) and (RABS<=0.30) then
            begin DE:=RABS; MANUAL:=true; writeln('DE=',DE:6:3) end
            else writeln('ОШИБКА: DE -0.30..0.30') end;
        CMD='DA=   ': begin GTNUM4(RABS,OK);
            if OK and (RABS>=-0.15) and (RABS<=0.15) then
            begin DA:=RABS; MANUAL:=true; writeln('DA=',DA:6:3) end
            else writeln('ОШИБКА: DA -0.15..0.15') end;
        CMD='DR=   ': begin GTNUM4(RABS,OK);
            if OK and (RABS>=-0.20) and (RABS<=0.20) then
            begin DR:=RABS; MANUAL:=true; writeln('DR=',DR:6:3) end
            else writeln('ОШИБКА: DR -0.20..0.20') end;
        CMD='TH=   ': begin GTNUM4(RABS,OK);
            if OK and (RABS>=0.0) and (RABS<=1.0) then
            begin DTZ:=RABS; MANUAL:=true; writeln('DTZ=',DTZ:6:3) end
            else writeln('ОШИБКА: TH 0.00..1.00') end;
        CMD='TRIM  ': begin DE:=0.0; DA:=0.0; DR:=0.0;
          writeln('ТРИМ: DE/DA/DR=0, ТЯГА СОХРАНЕНА') end;
        CMD='NEUT  ': begin DE:=0.0; DA:=0.0; DR:=0.0; DTZ:=0.0;
          MANUAL:=false; writeln('НЕЙТРАЛЬ: ВСЁ=0, AUTO PILOT') end;
        CMD='INJ   ': begin ASK; GTINT(IFLT,OK); GLFINJ(IFLT,U);
          RCEVT(IFLT,T); writeln('FAULT=',IFLT:1,' INJECTED') end;
        CMD='SCR   ': begin PRTSCR; PAUS:=true end;
        CMD='REC   ': begin RECCLR; RECON:=true;
          writeln('REC ON NSTEP=',NSTEP:1) end;
        CMD='RPL   ': begin RECON:=false; PLYREC end;
        CMD='RST   ': begin RECCLR; RECON:=false;
          writeln('REC CLEAR') end;
        CMD='STA   ': begin RUN:=true; PAUS:=false end;
        CMD='STE   ': begin DOSTP; PRFRM; PAUS:=true end;
        CMD='STO   ': begin RUN:=false; PAUS:=true end;
        CMD='PAR   ': begin PARAMS; INIT; PAUS:=true end;
        CMD='PRN   ': PRFRM;
        CMD='EXIT  ': begin writeln('EXIT'); stop end;
        true: writeln('NEPR. KOMANDA')
      end;
      (* В пилотной паузе одна команда возвращает управление полёту. *)
      if PILPAZ then
      begin
        PILPAZ:=false;
        if (IPILOT>0) and (CMD<>'STO   ') and (CMD<>'EXIT  ') and
           (CMD<>'FRZ   ') and (CMD<>'PILOT ') then
        begin RUN:=true; PAUS:=false end
      end
    end;
    if RUN then
    begin
      DOSTP;
      if RELHIT then
      begin
        PRFRM; writeln('STOLKNOVENIE S ZEMLEJ X11=',X[11]:7:0,
                ' VYS=',X[13]:7:1);
        GLSC(SUME,NEGL); SCCALC(X); JUDG(X);
        AVY:=abs(X[2]); OCE:=4;
        if AVY<=4.0 then OCE:=3;
        if AVY<=2.5 then OCE:=2;
        if AVY<=1.5 then OCE:=1;
        writeln('OCENKA= ',OCE:1);
        RUN:=false; PAUS:=true; RELHIT:=false
      end
      else
      begin
      if (NSTP mod NPRN)=0 then PRFRM;
      if X[13]<=VHCR then
      begin
        PRFRM; GLSC(SUME,NEGL); SCCALC(X); JUDG(X);
        AVY:=abs(X[2]); OCE:=4;
        if AVY<=4.0 then OCE:=3;
        if AVY<=2.5 then OCE:=2;
        if AVY<=1.5 then OCE:=1;
        writeln('OCENKA= ',OCE:1);
        if ICTRL>=2 then
          writeln('KONTROL ERMAX=',ERMAX:10:4);
          if ICTRL=3 then writeln('DTSH=',DTSH:8:4);
          if ICTRL=4 then writeln('DTCTRL=',DTCTRL:8:4);
        RUN:=false; PAUS:=true
      end;
      if X[13] < -100.0 then
      begin writeln('AVARIA: RAZRUSHENIE'); RUN:=false; PAUS:=true end;
      if NSTP>=NMAX then
      begin writeln('LIMIT VREMENI: T=',T:7:0);
            if ICTRL>=2 then
          writeln('KONTROL ERMAX=',ERMAX:10:4);
          if ICTRL=3 then writeln('DTSH=',DTSH:8:4);
          if ICTRL=4 then writeln('DTCTRL=',DTCTRL:8:4);
            RUN:=false; PAUS:=true end;
      (* Каденция запроса к пилоту отделена от печати кадра и ICTRL. *)
      if (not PAUS) and (IPILOT>0) and (NPILOT>0) and
         (NSTP mod NPILOT=0) then
      begin
        if (NSTP mod NPRN)<>0 then PRFRM;
        writeln('ЗАПРОС К ПИЛОТУ: ВВЕДИТЕ КОМАНДУ');
        PILPAZ:=true; RUN:=false; PAUS:=true
      end
      end
    end
  until false
end.

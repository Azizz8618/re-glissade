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
    KTIP,MODE,ICTRL,NFR,IFLIB,NPRN,NMAX,NSTP,NEGL,IPOS:integer;
    I,J,IH,JA,JG,IB,K,OCE:integer; OK,RUN,PAUS:boolean;
    IMODE,IEX:integer;
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
  write('> ');
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
var I:integer;
begin
  T:=T+DTSH;
  GLSET(T,DTSH,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX);
  if MODE=1 then GLAUTO(X,U) else PROGC(T,U);
  TURB;
  if ICTRL>=2 then
  begin
    KUTMER(X,U,DTSH,ERR);
    if ERR>ERMAX then ERMAX:=ERR
  end;
  PROIZV(X,U,VK1);
  for I:=1 to 13 do VX1[I]:=X[I]+0.5*DTSH*VK1[I];
  PROIZV(VX1,U,VK2);
  for I:=1 to 13 do VX2[I]:=X[I]+0.5*DTSH*VK2[I];
  PROIZV(VX2,U,VK3);
  for I:=1 to 13 do VX3[I]:=X[I]+DTSH*VK3[I];
  PROIZV(VX3,U,VK4);
  for I:=1 to 13 do
    X[I]:=X[I]+DTSH*(VK1[I]+2*VK2[I]+2*VK3[I]+VK4[I])/6.0;
  QN:=sqrt(X[4]*X[4]+X[5]*X[5]+X[6]*X[6]+X[7]*X[7]);
  X[4]:=X[4]/QN; X[5]:=X[5]/QN; X[6]:=X[6]/QN; X[7]:=X[7]/QN;
  EGLI:=X[13]+0.05241*X[11];
  SUME:=SUME+EGLI*EGLI; NEGL:=NEGL+1;
  NSTP:=NSTP+1
end;
(************************************************************)
procedure PRFRM;
var I,J,IH,JA,IB:integer; HGL:real;
begin
  GLANG(X,TH,GA,PS,DTM,EGLI,IPOS);
  GLVOD(VA,ALF);
  IB:=21+TRUNC(X[12]/5.0);
  if IB<1 then IB:=1;
  if IB>41 then IB:=41;
  writeln;
  writeln('T=',T:7:1,' TIP=',KTIP:1,' DALN=',DTM:7:0,
          ' VYS=',X[13]:7:1,' Y=',X[12]:7:1);
  writeln(' VYS PROFILE             | PLAN SVERHU');
  JA:=31-TRUNC(DTM/500.0);
  for IH:=8 downto 0 do
  begin
    write(' ',IH*100:4,' |');
    for J:=1 to 30 do
    begin
      HGL:=0.05241*(31-J)*500.0;
      if (IH=TRUNC(X[13]/100.0)) and (J=JA) then write('*')
      else if TRUNC(HGL/100.0)=IH then write('.')
      else if IH=0 then write('=')
      else write(' ')
    end;
    write(' |');
    if IH=8 then
    begin
      write('    |====|');
      for J:=1 to IB do write(' ');
      write('*'); writeln
    end
    else if IH=0 then writeln('    |====|')
    else writeln('    |    |')
  end;
  writeln('     15km  10km  5km  0');
  writeln(' GLISS 3 GR |----*----| EGLI=',EGLI:7:1,' M');
  writeln(' KURS LUCH |----*----| Y=',X[12]:7:1,' M');
  writeln(' SKOR=',VA:6:1,' VERT=',X[2]:6:2,
          ' ATAKA=',ALF:5:1,' TYAG=',100*U[4]:3:0)
end;
(************************************************************)
procedure CMDLOOP(var CMD:alfa);
begin
  if IMODE=0 then
    writeln('PIL: STA/STE/STO/PAR/PRN/AUTO/INS/EXIT')
  else
    writeln('INS: SEL/FRZ/UNF/INJ/REC/PLY/SCR/HLP/PIL');
  ASK; GTALF(CMD)
end;
(************************************************************)
begin
  PASTEL[3]:=[48];
  IMODE:=0; IEX:=1;
  PARAMS;
  INIT;
  PAUS:=true; RUN:=false;
  repeat
    if PAUS then
    begin
      CMDLOOP(CMD);
      select
        CMD='PIL   ': begin IMODE:=0; PAUS:=true end;
        CMD='INS   ': begin IMODE:=1; PAUS:=true end;
        CMD='FRZ   ': begin writeln('FREEZE');
          RUN:=false; PAUS:=true end;
        CMD='UNF   ': begin writeln('UNFREEZE');
          RUN:=true; PAUS:=false end;
        CMD='SEL   ': begin ASK; GTINT(IEX,OK);
          writeln('EXERCISE=',IEX:1,' SELECTED'); PAUS:=true end;
        CMD='HLP   ': if IMODE=0 then
          writeln('PIL: STA STE STO PAR PRN AUTO INS EXIT')
          else writeln('INS: SEL FRZ UNF INJ REC PLY SCR HLP PIL');
        CMD='STA   ': begin RUN:=true; PAUS:=false end;
        CMD='STE   ': begin DOSTP; PRFRM; PAUS:=true end;
        CMD='STO   ': begin RUN:=false; PAUS:=true end;
        CMD='PAR   ': begin PARAMS; INIT; PAUS:=true end;
        CMD='PRN   ': PRFRM;
        CMD='EXIT  ': begin writeln('EXIT'); stop end;
        true: writeln('NEPR. KOMANDA')
      end
    end;
    if RUN then
    begin
      DOSTP;
      if (NSTP mod NPRN)=0 then PRFRM;
      if X[13]<=VHCR then
      begin
        PRFRM; GLSC(SUME,NEGL); JUDG(X);
        AVY:=abs(X[2]); OCE:=4;
        if AVY<=4.0 then OCE:=3;
        if AVY<=2.5 then OCE:=2;
        if AVY<=1.5 then OCE:=1;
        writeln('OCENKA= ',OCE:1);
        if ICTRL>=2 then
          writeln('KONTROL ERMAX=',ERMAX:10:4);
        RUN:=false; PAUS:=true
      end;
      if X[13] < -100.0 then
      begin writeln('AVARIA: RAZRUSHENIE'); RUN:=false; PAUS:=true end;
      if NSTP>=NMAX then
      begin writeln('LIMIT VREMENI: T=',T:7:0);
            if ICTRL>=2 then
          writeln('KONTROL ERMAX=',ERMAX:10:4);
            RUN:=false; PAUS:=true end;
      if (not PAUS) and (NSTP mod NPRN=0) and (ICTRL=1)
      then CMDLOOP(CMD)
    end
  until false
end.

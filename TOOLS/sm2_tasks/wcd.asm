; выдающая перекодировка: запись результата
; Прототип: re-mrv/src/ps/, src/rcd/, src/wcd/
            .ORG    0
START:      LDA     A
            ADA     B
            STA     RES
            HLT
            .ORG    000020
A:          .WORD   55
B:          .WORD   7
RES:        .WORD   0
            .END

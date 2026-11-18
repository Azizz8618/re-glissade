; модель подсистемы 2: счётчик с периодом
; Прототип: re-mrv/src/ps/, src/rcd/, src/wcd/
            .ORG    0
START:      LDA     A
            ADA     B
            STA     RES
            HLT
            .ORG    000020
A:          .WORD   11
B:          .WORD   1
RES:        .WORD   0
            .END

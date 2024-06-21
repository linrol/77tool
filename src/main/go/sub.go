package main

import "C"

//export subtract
func subtract(a, b int) int {
    return a - b
}
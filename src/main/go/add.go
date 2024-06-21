package main

import "C"

//export add
func add(a, b int) int {
    return a + b
}

func main() {
    // Need a main function to compile Go code
}
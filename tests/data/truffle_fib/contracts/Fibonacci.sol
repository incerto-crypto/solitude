pragma solidity ^0.5.8;

contract Fibonacci {
    function fib_r(uint n) internal pure returns (uint) {
        if (n < 2) {
            return n;
        }
        return fib_r(n - 1) + fib_r(n - 2);
    }
}

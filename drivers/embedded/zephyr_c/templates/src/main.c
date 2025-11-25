#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

int main(void)
{
    while (1) {
        printk("Zephyr scaffold running...\n");
        k_sleep(K_MSEC(1000));
    }
    return 0;
}


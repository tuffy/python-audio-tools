#include <stdint.h>

#define KEY_SIZE 5

typedef uint8_t dvd_key_t[KEY_SIZE];

typedef struct {
    int       protection;
    int       agid;
    dvd_key_t p_bus_key;
    dvd_key_t p_disc_key;
    dvd_key_t p_title_key;
} css_t;

int
GetBusKey(int i_fd, css_t* css);

int
GetASF(int i_fd);

void
CryptKey(int i_key_type, int i_variant,
         uint8_t const *p_challenge, uint8_t *p_key);

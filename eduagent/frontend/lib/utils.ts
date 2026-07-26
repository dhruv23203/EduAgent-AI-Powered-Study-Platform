// Add your utility functions here
export const cn = (...classes: (string | undefined)[]) => {
  return classes.filter(Boolean).join(" ");
};
